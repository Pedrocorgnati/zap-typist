"""Configuracoes centrais do app via pydantic-settings.

Hoje cobre apenas flags transversais (DEBUG, LOG_LEVEL); paths XDG continuam
em `zap_typist.config.paths` por dependerem de reload em testes monkeypatched.
ENVs do desktop (XDG_SESSION_TYPE, WAYLAND_DISPLAY) sao lidas direto em
`zap_typist.app._is_wayland` por nao serem configuracao do app.
"""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZAP_TYPIST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


settings = Settings()


__all__ = ["Settings", "settings"]
