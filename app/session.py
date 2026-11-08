"""Consulta em andamento. Vive só em memória (R7, R8)."""
from __future__ import annotations

from enum import Enum, auto


class Estado(Enum):
    OCIOSO = auto()
    GRAVANDO = auto()
    PAUSADO = auto()
    PROCESSANDO = auto()
    REVISAO = auto()


class Session:
    def __init__(self):
        self.limpar()

    def limpar(self) -> None:
        self.estado = Estado.OCIOSO
        self.segundos = 0
        self.blocos: list[str] = []
        self.valores: dict[str, object] = {}

    @property
    def transcricao(self) -> str:
        return "\n".join(self.blocos)
