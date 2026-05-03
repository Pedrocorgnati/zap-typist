"""Testes unitários para zap_typist.utils.e164."""
from __future__ import annotations

import pytest

from zap_typist.utils.e164 import (
    e164_from_lead_fields,
    format_e164,
    parse_raw_phone,
    validate_e164,
)


class TestFormatE164:
    def test_9_digit_number(self) -> None:
        assert format_e164("11", "98765", "4321") == "+5511987654321"

    def test_8_digit_number(self) -> None:
        assert format_e164("11", "8765", "4321") == "+551187654321"

    def test_strips_whitespace(self) -> None:
        assert format_e164("  11  ", "  98765  ", "  4321  ") == "+5511987654321"

    def test_invalid_ddd_empty(self) -> None:
        assert format_e164("", "98765", "4321") is None

    def test_invalid_ddd_unknown(self) -> None:
        assert format_e164("00", "98765", "4321") is None
        assert format_e164("20", "98765", "4321") is None
        assert format_e164("39", "98765", "4321") is None

    def test_invalid_sufixo_too_short(self) -> None:
        assert format_e164("11", "98765", "43") is None

    def test_non_digit_fields(self) -> None:
        assert format_e164("11", "abcde", "4321") is None
        assert format_e164("11", "98765", "abcd") is None

    def test_number_too_short_or_long(self) -> None:
        assert format_e164("11", "987", "6543") is None
        assert format_e164("11", "98765", "432100") is None

    def test_9_digit_without_9_initial(self) -> None:
        assert format_e164("11", "18765", "4321") is None
        assert format_e164("11", "28765", "4321") is None

    def test_sp_ddd(self) -> None:
        assert format_e164("11", "99999", "0000") == "+5511999990000"

    def test_nordeste_ddd(self) -> None:
        assert format_e164("85", "98765", "4321") == "+5585987654321"


class TestValidateE164:
    def test_valid_9_digit(self) -> None:
        assert validate_e164("+5511987654321") is True

    def test_valid_8_digit(self) -> None:
        assert validate_e164("+551187654321") is True

    def test_no_plus_prefix(self) -> None:
        assert validate_e164("5511987654321") is False

    def test_no_br_code(self) -> None:
        assert validate_e164("+1187654321") is False

    def test_non_digit_chars(self) -> None:
        assert validate_e164("+55abcdefg") is False

    def test_too_short(self) -> None:
        assert validate_e164("+5511") is False


class TestParseRawPhone:
    def test_formatted_with_spaces_and_parens(self) -> None:
        result = parse_raw_phone("+55 (11) 9 8765-4321")
        assert result == ("11", "98765", "4321")

    def test_plain_11_digits(self) -> None:
        result = parse_raw_phone("11987654321")
        assert result == ("11", "98765", "4321")

    def test_plain_10_digits(self) -> None:
        result = parse_raw_phone("1187654321")
        assert result == ("11", "8765", "4321")

    def test_with_country_code_no_plus(self) -> None:
        result = parse_raw_phone("5511987654321")
        assert result == ("11", "98765", "4321")

    def test_invalid_too_short(self) -> None:
        assert parse_raw_phone("1234") is None

    def test_invalid_ddd(self) -> None:
        assert parse_raw_phone("00987654321") is None

    def test_garbage_input(self) -> None:
        assert parse_raw_phone("hello world") is None


class TestE164FromLeadFields:
    def test_raises_on_invalid(self) -> None:
        with pytest.raises(ValueError, match=r"Campos inválidos.*ddd=''"):
            e164_from_lead_fields("", "98765", "4321")

    def test_returns_e164_on_valid(self) -> None:
        assert e164_from_lead_fields("11", "98765", "4321") == "+5511987654321"
