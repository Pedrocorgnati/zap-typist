"""Testes de form_validators (TASK-4 do module-2-shared-foundations)."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QValidator

from zap_typist.db.models import LeadStatus
from zap_typist.ui.widgets.form_validators import (
    _TRANSITIONS,
    DddValidator,
    LeadStatusGuard,
    PhoneSegmentValidator,
    validate_settings_key,
)


class TestLeadStatusGuard:
    """Cobertura da máquina de estados."""

    def test_all_lead_statuses_have_transitions_defined(self):
        """Cada valor de LeadStatus deve estar como chave em _TRANSITIONS."""
        missing = set(LeadStatus) - set(_TRANSITIONS.keys())
        assert not missing, f"Status sem transição: {missing}"

    def test_pendente_to_query_gerada_allowed(self):
        assert LeadStatusGuard.can_transition(
            LeadStatus.pendente, LeadStatus.query_gerada
        ) is True

    def test_pendente_to_descartado_allowed(self):
        assert LeadStatusGuard.can_transition(
            LeadStatus.pendente, LeadStatus.descartado
        ) is True

    def test_pendente_to_enviado_blocked(self):
        """Salto de etapas é proibido — pendente não vai direto para enviado."""
        assert LeadStatusGuard.can_transition(
            LeadStatus.pendente, LeadStatus.enviado
        ) is False

    def test_enviado_to_pendente_blocked(self):
        """Regress proibida: enviado nunca volta para pendente."""
        assert LeadStatusGuard.can_transition(
            LeadStatus.enviado, LeadStatus.pendente
        ) is False

    def test_enviado_only_to_falhou(self):
        """enviado aceita apenas transição para falhou (retry técnico)."""
        assert LeadStatusGuard.allowed_next(LeadStatus.enviado) == [LeadStatus.falhou]

    def test_falhou_can_retry_to_mensagem_pronta(self):
        assert LeadStatusGuard.can_transition(
            LeadStatus.falhou, LeadStatus.mensagem_pronta
        ) is True

    def test_descartado_is_terminal(self):
        assert LeadStatusGuard.is_terminal(LeadStatus.descartado) is True
        assert LeadStatusGuard.allowed_next(LeadStatus.descartado) == []
        assert LeadStatusGuard.can_transition(
            LeadStatus.descartado, LeadStatus.pendente
        ) is False

    def test_invalido_is_terminal(self):
        assert LeadStatusGuard.is_terminal(LeadStatus.invalido) is True
        assert LeadStatusGuard.allowed_next(LeadStatus.invalido) == []

    def test_pendente_not_terminal(self):
        assert LeadStatusGuard.is_terminal(LeadStatus.pendente) is False

    def test_allowed_next_pendente_contains_expected(self):
        next_statuses = LeadStatusGuard.allowed_next(LeadStatus.pendente)
        assert LeadStatus.query_gerada in next_statuses
        assert LeadStatus.descartado in next_statuses
        assert len(next_statuses) == 2

    def test_allowed_next_returns_copy(self):
        """allowed_next retorna cópia — mutar resultado não afeta _TRANSITIONS."""
        result = LeadStatusGuard.allowed_next(LeadStatus.pendente)
        result.append(LeadStatus.enviado)
        assert LeadStatus.enviado not in _TRANSITIONS[LeadStatus.pendente]

    def test_query_gerada_to_telefone_preenchido_allowed(self):
        assert LeadStatusGuard.can_transition(
            LeadStatus.query_gerada, LeadStatus.telefone_preenchido
        ) is True


class TestDddValidator:
    """Cobertura do QValidator de DDD."""

    @pytest.fixture
    def validator(self):
        return DddValidator()

    def test_empty_is_intermediate(self, validator):
        state, _, _ = validator.validate("", 0)
        assert state == QValidator.State.Intermediate

    def test_one_digit_is_intermediate(self, validator):
        state, _, _ = validator.validate("1", 1)
        assert state == QValidator.State.Intermediate

    def test_valid_ddd_11_acceptable(self, validator):
        state, _, _ = validator.validate("11", 2)
        assert state == QValidator.State.Acceptable

    def test_invalid_ddd_00_rejected(self, validator):
        state, _, _ = validator.validate("00", 2)
        assert state == QValidator.State.Invalid

    def test_non_digit_rejected(self, validator):
        state, _, _ = validator.validate("1a", 2)
        assert state == QValidator.State.Invalid

    def test_three_digits_rejected(self, validator):
        state, _, _ = validator.validate("123", 3)
        assert state == QValidator.State.Invalid


class TestPhoneSegmentValidator:
    """Cobertura do QValidator de prefixo/sufixo."""

    def test_constructor_rejects_invalid_lengths(self):
        with pytest.raises(ValueError):
            PhoneSegmentValidator(min_len=-1, max_len=4)
        with pytest.raises(ValueError):
            PhoneSegmentValidator(min_len=5, max_len=4)

    def test_prefix_4_to_5_accepts_4_digits(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("9876", 4)
        assert state == QValidator.State.Acceptable

    def test_prefix_4_to_5_accepts_5_digits(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("98765", 5)
        assert state == QValidator.State.Acceptable

    def test_prefix_4_to_5_rejects_6_digits(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("987654", 6)
        assert state == QValidator.State.Invalid

    def test_partial_input_intermediate(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("98", 2)
        assert state == QValidator.State.Intermediate

    def test_empty_intermediate(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("", 0)
        assert state == QValidator.State.Intermediate

    def test_non_digit_rejected(self):
        v = PhoneSegmentValidator(min_len=4, max_len=5)
        state, _, _ = v.validate("9a", 2)
        assert state == QValidator.State.Invalid

    def test_suffix_exact_4(self):
        v = PhoneSegmentValidator(min_len=4, max_len=4)
        state, _, _ = v.validate("4321", 4)
        assert state == QValidator.State.Acceptable


class TestValidateSettingsKey:
    """Cobertura da função pura de validação de chave."""

    def test_valid_key(self):
        assert validate_settings_key("msg_template_1") is True

    def test_valid_key_with_dash(self):
        assert validate_settings_key("with-dash_and_underscore") is True

    def test_empty_rejected(self):
        assert validate_settings_key("") is False

    def test_internal_space_rejected(self):
        assert validate_settings_key("invalid key") is False

    def test_leading_space_rejected(self):
        assert validate_settings_key(" leading") is False

    def test_trailing_space_rejected(self):
        assert validate_settings_key("trailing ") is False

    def test_only_whitespace_rejected(self):
        assert validate_settings_key("   ") is False
