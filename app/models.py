"""Templates de campos: o único dado persistente do programa (R2, R8)."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
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


NOME_PADRAO = "Usuário comum"


@dataclass
class Template:
    nome: str
    campos: list[Field] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"nome": self.nome, "campos": [c.to_dict() for c in self.campos]}

    @staticmethod
    def from_dict(d: dict) -> "Template":
        return Template(nome=d["nome"], campos=[Field.from_dict(c) for c in d.get("campos", [])])


@dataclass
class Configuracao:
    templates: list[Template] = field(default_factory=list)
    ativo: str = NOME_PADRAO

    def __post_init__(self):
        if not self.templates:
            self.templates = [Template(NOME_PADRAO)]
        if self.ativo not in [t.nome for t in self.templates]:
            self.ativo = self.templates[0].nome

    @property
    def campos_ativos(self) -> list[Field]:
        return next(t.campos for t in self.templates if t.nome == self.ativo)


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


class ConfigStore:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = path

    def load(self) -> Configuracao:
        if not self.path.exists():
            return Configuracao()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if "templates" in data:
                templates = [Template.from_dict(t) for t in data["templates"]]
                return Configuracao(templates, data.get("ativo", ""))
            # Formato antigo, com uma única lista de campos.
            campos = [Field.from_dict(d) for d in data.get("campos", [])]
            return Configuracao([Template(NOME_PADRAO, campos)])
        except (json.JSONDecodeError, KeyError, ValueError):
            return Configuracao()

    def save(self, config: Configuracao) -> None:
        payload = {"ativo": config.ativo, "templates": [t.to_dict() for t in config.templates]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
