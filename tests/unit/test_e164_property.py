"""Property-based tests para zap_typist.utils.e164 usando hypothesis."""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from zap_typist.utils.e164 import (
    _DDD_VALID,
    format_e164,
    parse_raw_phone,
    validate_e164,
)

_VALID_DDD = st.sampled_from(sorted(_DDD_VALID))
_DIGITS_4 = st.text(alphabet="0123456789", min_size=4, max_size=4)
_DIGITS_5 = st.text(alphabet="0123456789", min_size=5, max_size=5)
# Móvel BR pós-2012: prefixo de 5 dígitos sempre começa com "9"
_DIGITS_5_MOBILE = st.text(alphabet="0123456789", min_size=4, max_size=4).map(lambda s: "9" + s)


class TestProperties:
    @given(ddd=_VALID_DDD, prefixo=_DIGITS_5_MOBILE, sufixo=_DIGITS_4)
    def test_roundtrip_9_digits(self, ddd: str, prefixo: str, sufixo: str) -> None:
        e164 = format_e164(ddd, prefixo, sufixo)
        assert e164 is not None
        parsed = parse_raw_phone(e164)
        assert parsed == (ddd, prefixo, sufixo)

    @given(ddd=_VALID_DDD, prefixo=_DIGITS_4, sufixo=_DIGITS_4)
    def test_roundtrip_8_digits(self, ddd: str, prefixo: str, sufixo: str) -> None:
        e164 = format_e164(ddd, prefixo, sufixo)
        assert e164 is not None
        parsed = parse_raw_phone(e164)
        assert parsed == (ddd, prefixo, sufixo)

    @given(ddd=_VALID_DDD, prefixo=_DIGITS_5, sufixo=_DIGITS_4)
    def test_format_then_validate_always_true(
        self, ddd: str, prefixo: str, sufixo: str
    ) -> None:
        e164 = format_e164(ddd, prefixo, sufixo)
        if e164 is not None:
            assert validate_e164(e164) is True

    @given(
        ddd=st.text(alphabet="0123456789", min_size=2, max_size=2).filter(
            lambda x: x not in _DDD_VALID
        ),
        prefixo=_DIGITS_5,
        sufixo=_DIGITS_4,
    )
    def test_unknown_ddd_returns_none(
        self, ddd: str, prefixo: str, sufixo: str
    ) -> None:
        assert format_e164(ddd, prefixo, sufixo) is None

    @given(ddd=_VALID_DDD, prefixo=_DIGITS_5_MOBILE, sufixo=_DIGITS_4)
    def test_length_invariant_9_digits(self, ddd: str, prefixo: str, sufixo: str) -> None:
        e164 = format_e164(ddd, prefixo, sufixo)
        assert e164 is not None
        assert len(e164) == 14  # "+55" + 2 (ddd) + 9 (numero)

    @given(ddd=_VALID_DDD, prefixo=_DIGITS_4, sufixo=_DIGITS_4)
    def test_length_invariant_8_digits(self, ddd: str, prefixo: str, sufixo: str) -> None:
        e164 = format_e164(ddd, prefixo, sufixo)
        assert e164 is not None
        assert len(e164) == 13  # "+55" + 2 (ddd) + 8 (numero — linha fixa)
