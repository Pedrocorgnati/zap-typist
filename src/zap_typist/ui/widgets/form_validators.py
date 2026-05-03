"""form_validators — Qt validators de domínio + LeadStatusGuard.

Contratos (module-2-shared-foundations):
- DddValidator(QValidator): valida DDD brasileiro (2 dígitos numéricos da lista
  canônica DDDS_VALIDOS_BR, importada de utils.e164).
- PhoneSegmentValidator(min_len, max_len): valida prefixo/sufixo numérico
  com comprimento configurável.
- LeadStatusGuard: máquina de estados de LeadStatus pré-computada.
  - can_transition(current, next_status) -> bool
  - allowed_next(current) -> list[LeadStatus]
  - is_terminal(status) -> bool
- validate_settings_key(key): chave de settings (string não-vazia, sem
  whitespace nas bordas, sem espaços internos).

Consumidores: module-3 (Aba1 form), module-4 (Aba2 form), module-5 (Aba4 form),
module-6a (DispatchEngine — usa LeadStatusGuard para validar transições antes
do commit no DB).

Decisão de consolidação: LeadStatusGuard mora aqui (e não em
domain/lead_state_machine.py) porque é semanticamente um validador de domínio
e mantém o número de módulos baixo. Refactor para arquivo próprio só se a
máquina crescer com side effects/hooks.
"""

from __future__ import annotations

from PySide6.QtGui import QValidator

from zap_typist.db.models import LeadStatus
from zap_typist.utils.e164 import DDDS_VALIDOS_BR

__all__ = [
    "DddValidator",
    "LeadStatusGuard",
    "PhoneSegmentValidator",
    "validate_settings_key",
]


# ---------------------------------------------------------------------------
# Máquina de estados de LeadStatus (fonte da verdade do projeto).
# Estados terminais têm lista vazia (descartado, invalido).
# ---------------------------------------------------------------------------
_TRANSITIONS: dict[LeadStatus, list[LeadStatus]] = {
    LeadStatus.pendente: [
        LeadStatus.query_gerada,
        LeadStatus.descartado,
    ],
    LeadStatus.query_gerada: [
        LeadStatus.telefone_preenchido,
        LeadStatus.descartado,
    ],
    LeadStatus.telefone_preenchido: [
        LeadStatus.mensagem_pronta,
        LeadStatus.whatsapp_inexistente,
        LeadStatus.descartado,
    ],
    LeadStatus.mensagem_pronta: [
        LeadStatus.whatsapp_valido,
        LeadStatus.whatsapp_inexistente,
        LeadStatus.descartado,
    ],
    LeadStatus.whatsapp_valido: [
        LeadStatus.enviado,
        LeadStatus.falhou,
        LeadStatus.descartado,
    ],
    LeadStatus.whatsapp_inexistente: [
        LeadStatus.descartado,
        LeadStatus.invalido,
    ],
    LeadStatus.enviado: [
        LeadStatus.falhou,  # retry técnico após confirmação tardia de falha
    ],
    LeadStatus.falhou: [
        LeadStatus.mensagem_pronta,  # retry da mensagem
        LeadStatus.descartado,
        LeadStatus.invalido,
    ],
    LeadStatus.descartado: [],  # terminal
    LeadStatus.invalido: [],  # terminal
}


class LeadStatusGuard:
    """Encapsula a máquina de estados de LeadStatus.

    Todos os métodos são estáticos — `_TRANSITIONS` é read-only após import.
    Performance: `can_transition` faz 1 lookup em dict + 1 verificação `in`
    sobre lista de até 3 elementos — < 0.1ms por chamada.
    """

    @staticmethod
    def can_transition(current: LeadStatus, next_status: LeadStatus) -> bool:
        """Retorna True se `current → next_status` é uma transição permitida."""
        return next_status in _TRANSITIONS.get(current, [])

    @staticmethod
    def allowed_next(current: LeadStatus) -> list[LeadStatus]:
        """Retorna lista (cópia) dos próximos estados válidos a partir de `current`."""
        return list(_TRANSITIONS.get(current, []))

    @staticmethod
    def is_terminal(status: LeadStatus) -> bool:
        """Retorna True se `status` não admite mais transições (terminal)."""
        return len(_TRANSITIONS.get(status, [])) == 0


# ---------------------------------------------------------------------------
# Qt Validators reutilizáveis (puros — não exigem QApplication para validate()).
# ---------------------------------------------------------------------------
class DddValidator(QValidator):
    """Valida DDD brasileiro: 2 dígitos numéricos contidos em DDDS_VALIDOS_BR.

    Estados:
    - vazio                        → Intermediate (usuário ainda digitando)
    - 1 dígito numérico            → Intermediate
    - 2 dígitos em DDDS_VALIDOS_BR → Acceptable
    - 2 dígitos não-canônicos      → Invalid
    - qualquer caractere não-num   → Invalid
    - mais de 2 dígitos            → Invalid
    """

    def validate(
        self, input_str: str, pos: int
    ) -> tuple[QValidator.State, str, int]:
        if input_str == "":
            return QValidator.State.Intermediate, input_str, pos
        if not input_str.isdigit():
            return QValidator.State.Invalid, input_str, pos
        if len(input_str) > 2:
            return QValidator.State.Invalid, input_str, pos
        if len(input_str) == 2:
            if input_str in DDDS_VALIDOS_BR:
                return QValidator.State.Acceptable, input_str, pos
            return QValidator.State.Invalid, input_str, pos
        # len(input_str) == 1 → ainda digitando
        return QValidator.State.Intermediate, input_str, pos


class PhoneSegmentValidator(QValidator):
    """Valida prefixo/sufixo numérico com comprimento configurável.

    Args:
        min_len: comprimento mínimo aceitável (Acceptable a partir daqui)
        max_len: comprimento máximo aceitável (Invalid se exceder)

    Exemplos brasileiros:
    - prefixo móvel:  PhoneSegmentValidator(min_len=4, max_len=5)  # 9876 ou 98765
    - prefixo fixo:   PhoneSegmentValidator(min_len=4, max_len=4)  # 3333
    - sufixo:         PhoneSegmentValidator(min_len=4, max_len=4)  # 4321
    """

    def __init__(self, min_len: int, max_len: int, parent: object | None = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        if min_len < 0 or max_len < min_len:
            raise ValueError(
                f"PhoneSegmentValidator: min_len={min_len}, max_len={max_len} inválidos"
            )
        self.min_len = min_len
        self.max_len = max_len

    def validate(
        self, input_str: str, pos: int
    ) -> tuple[QValidator.State, str, int]:
        if input_str == "":
            return QValidator.State.Intermediate, input_str, pos
        if not input_str.isdigit():
            return QValidator.State.Invalid, input_str, pos
        if len(input_str) > self.max_len:
            return QValidator.State.Invalid, input_str, pos
        if len(input_str) >= self.min_len:
            return QValidator.State.Acceptable, input_str, pos
        return QValidator.State.Intermediate, input_str, pos


# ---------------------------------------------------------------------------
# Validador puro de chave de settings (sem Qt).
# ---------------------------------------------------------------------------
def validate_settings_key(key: str) -> bool:
    """Valida que uma chave de settings é não-vazia, sem espaços e trimada.

    Aceitos:  "msg_template_1", "delay_ms", "with-dash"
    Rejeitados: "", "  ", "leading ", " trailing", "key with space"
    """
    return bool(key) and " " not in key and key == key.strip()
