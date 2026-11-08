"""Configuração de campos: o único dado persistente do programa (R2, R8)."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class FieldType(str, Enum):
    TEXTO = "texto"
    TEXTO_LONGO = "texto_longo"
    INTEIRO = "inteiro"
    DECIMAL = "decimal"
    CHECKBOX = "checkbox"

    @property
    def rotulo(self) -> str:
        return {
            FieldType.TEXTO: "Texto simples",
            FieldType.TEXTO_LONGO: "Texto longo",
            FieldType.INTEIRO: "Inteiro",
            FieldType.DECIMAL: "Decimal",
            FieldType.CHECKBOX: "Checkbox",
        }[self]


@dataclass
class Field:
    nome: str
    contexto: str
    tipo: FieldType

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tipo"] = self.tipo.value
        return d

    @staticmethod
    def from_dict(d: dict) -> "Field":
        return Field(nome=d["nome"], contexto=d.get("contexto", ""), tipo=FieldType(d["tipo"]))


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path

    def load(self) -> list[Field]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Field.from_dict(d) for d in data.get("campos", [])]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def save(self, campos: list[Field]) -> None:
        payload = {"campos": [c.to_dict() for c in campos]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
