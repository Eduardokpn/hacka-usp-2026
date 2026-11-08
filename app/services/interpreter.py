"""Interpretação mockada. No futuro: API da DeepSeek (deepseek-flash, json_object, temperatura 0).

O prompt e a validação por tipo são reais; só a resposta do modelo é simulada.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata

from app.models import Field, FieldType

INSTRUCAO = (
    "Instrução: preencha os campos com base na consulta, em vocabulário médico.\n"
    "Se a consulta não trouxer a informação de um campo, deixe-o vazio. Não invente.\n"
    "Responda apenas com um objeto JSON cujas chaves são os nomes dos campos."
)


def build_prompt(transcricao: str, campos: list[Field]) -> str:
    linhas = [INSTRUCAO, "", "Campos:"]
    for c in campos:
        linhas.append(f"- {c.nome} ({c.tipo.rotulo.lower()}): {c.contexto}".rstrip(": "))
    linhas += ["", "Transcrição:", f'"{transcricao}"']
    return "\n".join(linhas)


# ---------------------------------------------------------------- mock ----

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()


# Ordem importa: a primeira regra que casar com nome/contexto vence.
# Cada regra: (padrões regex, valores por tipo; "*" vale para qualquer tipo).
_REGRAS: list[tuple[list[str], dict]] = [
    ([r"\bqueixa", r"\bmotivo"], {
        "*": "Cefaleia e febre há 3 dias.",
    }),
    ([r"\bhistoria", r"\bhda\b", r"\bevolucao"], {
        "*": ("Paciente refere cefaleia de início insidioso há 3 dias, de intensidade progressiva, "
              "associada a febre e mialgia a partir do segundo dia. Relata odinofagia leve. "
              "Nega tosse e dispneia."),
    }),
    ([r"\btemperatura", r"\btax\b", r"\btemp\b"], {
        "*": "37,8",
    }),
    ([r"frequencia cardiaca", r"\bfc\b", r"\bpulso", r"\bbatimento"], {
        "*": 88,
    }),
    ([r"\bsistolica"], {"*": 120}),
    ([r"\bdiastolica"], {"*": 80}),
    ([r"\bpressao", r"\bpa\b"], {
        FieldType.INTEIRO: 120,
        "*": "120 x 80 mmHg",
    }),
    ([r"\bsatura", r"\bspo2"], {"*": 97}),
    ([r"\bpeso"], {"*": "68"}),
    ([r"\btabag", r"\bfuma", r"\bcigarr"], {
        FieldType.CHECKBOX: True,
        FieldType.INTEIRO: 10,
        "*": "Tabagista ativo, cerca de 10 cigarros/dia.",
    }),
    ([r"\balergi"], {
        FieldType.CHECKBOX: True,
        "*": "Dipirona.",
    }),
    ([r"\bfebre"], {
        FieldType.CHECKBOX: True,
        "*": "Febre há 2 dias, aferida 37,8 °C na consulta.",
    }),
    ([r"exame fisico", r"\bexame\b", r"\boroscopia", r"\borofaringe"], {
        "*": "Orofaringe com hiperemia leve, sem exsudato. FC 88 bpm, PA 120x80 mmHg, Tax 37,8 °C, SpO2 97%.",
    }),
    ([r"\bconduta", r"\bplano", r"\borienta"], {
        "*": "Repouso e hidratação oral. Retorno se piora ou persistência da febre.",
    }),
    ([r"\bsintoma"], {
        "*": "Cefaleia, febre, mialgia e odinofagia leve.",
    }),
]


class MockInterpreter:
    """Simula a resposta JSON da DeepSeek casando o campo com palavras-chave."""

    LATENCIA_S = 1.5

    def interpretar(self, transcricao: str, campos: list[Field]) -> dict:
        self.ultimo_prompt = build_prompt(transcricao, campos)
        time.sleep(self.LATENCIA_S)
        resposta = {}
        for c in campos:
            alvo = _norm(f"{c.nome} {c.contexto}")
            valor = None
            for padroes, valores in _REGRAS:
                if any(re.search(p, alvo) for p in padroes):
                    valor = valores.get(c.tipo, valores.get("*"))
                    break
            resposta[c.nome] = valor
        # Ida e volta em JSON, como viria da API.
        bruto = json.loads(json.dumps(resposta, ensure_ascii=False))
        return validar_resposta(bruto, campos)


# ----------------------------------------------------------- validação ----

def validar_por_tipo(tipo: FieldType, valor):
    """Converte o valor bruto do modelo para o tipo do campo; inválido vira vazio (None)."""
    if valor is None:
        return None
    if tipo in (FieldType.TEXTO, FieldType.TEXTO_LONGO):
        if isinstance(valor, (dict, list)):
            return None
        texto = str(valor).strip()
        return texto or None
    if tipo == FieldType.INTEIRO:
        if isinstance(valor, bool):
            return None
        if isinstance(valor, int):
            return valor
        if isinstance(valor, float):
            return int(valor) if valor.is_integer() else None
        m = re.fullmatch(r"\s*(-?\d+)\s*", str(valor))
        return int(m.group(1)) if m else None
    if tipo == FieldType.DECIMAL:
        if isinstance(valor, bool):
            return None
        if isinstance(valor, (int, float)):
            return float(valor)
        m = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*", str(valor))
        return float(m.group(1).replace(",", ".")) if m else None
    if tipo == FieldType.CHECKBOX:
        if isinstance(valor, bool):
            return valor
        s = _norm(str(valor)).strip()
        if s in ("sim", "s", "true", "yes"):
            return True
        if s in ("nao", "n", "false", "no"):
            return False
        return None
    return None


def validar_resposta(bruto: dict, campos: list[Field]) -> dict:
    if not isinstance(bruto, dict):
        return {c.nome: None for c in campos}
    return {c.nome: validar_por_tipo(c.tipo, bruto.get(c.nome)) for c in campos}


def formatar_valor(tipo: FieldType, valor) -> str:
    """O que vai para o Ctrl+C (tabela de tipos da seção 04)."""
    if valor is None:
        return ""
    if tipo == FieldType.DECIMAL:
        texto = f"{valor:.2f}".rstrip("0").rstrip(".")
        return texto.replace(".", ",")
    if tipo == FieldType.CHECKBOX:
        return "Sim" if valor else "Não"
    return str(valor)
