"""Widgets reutilizáveis do Zap Typist (terminal, validators, status guard)."""

from zap_typist.ui.widgets.form_validators import (
    DddValidator,
    LeadStatusGuard,
    PhoneSegmentValidator,
    validate_settings_key,
)
from zap_typist.ui.widgets.terminal_widget import TerminalWidget

__all__ = [
    "DddValidator",
    "LeadStatusGuard",
    "PhoneSegmentValidator",
    "TerminalWidget",
    "validate_settings_key",
]
