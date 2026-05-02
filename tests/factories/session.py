"""Stubs minimos de SessionFactory para testes de seed."""

from __future__ import annotations

from typing import Any


class StubSessionFactory:
    """Stub minimo: callable retorna sessao fixa, .remove() no-op.

    Usado por fixtures que precisam injetar uma sessao SQLAlchemy in-memory
    no lugar de zap_typist.db.seed.SessionFactory.
    """

    def __init__(self, session: Any) -> None:
        self._session = session

    def __call__(self) -> Any:
        return self._session

    def remove(self) -> None:
        return None
