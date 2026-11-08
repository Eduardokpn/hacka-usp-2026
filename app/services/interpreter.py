"""Preenchimento dos campos da configuração a partir da transcrição, com a API do Gemini."""
from __future__ import annotations

import json
import os
import re
import unicodedata

from app.models import Field, FieldType
from app.services.http import ServicoErro, post_com_retry

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODELO_PADRAO = "gemini-3.5-flash-lite"

INSTRUCAO = (
    "Instrução: preencha os campos com base na consulta, em vocabulário médico.\n"
    "Se a consulta não trouxer a informação de um campo, use null. Não invente.\n"
    "Responda apenas com um objeto JSON cujas chaves são os nomes dos campos."
)


def build_prompt(transcricao: str, campos: list[Field]) -> str:
    linhas = [INSTRUCAO, "", "Campos:"]
    for c in campos:
        linhas.append(f"- {c.nome} ({c.tipo.rotulo.lower()}): {c.contexto}".rstrip(": "))
    linhas += ["", "Transcrição:", f'"{transcricao}"']
    return "\n".join(linhas)


# --------------------------------------------------------------- Gemini ----

_TIPOS_SCHEMA = {
    FieldType.TEXTO: "STRING",
    FieldType.TEXTO_LONGO: "STRING",
    FieldType.INTEIRO: "INTEGER",
    FieldType.DECIMAL: "NUMBER",
    FieldType.CHECKBOX: "BOOLEAN",
}


def _schema(campos: list[Field]) -> dict:
    return {
        "type": "OBJECT",
        "properties": {c.nome: {"type": _TIPOS_SCHEMA[c.tipo], "nullable": True} for c in campos},
        "required": [c.nome for c in campos],
    }


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()


class GeminiInterpreter:
    """Preenche os campos da configuração a partir da transcrição."""

    def interpretar(self, transcricao: str, campos: list[Field]) -> dict:
        if not transcricao.strip():
            return {c.nome: None for c in campos}
        chave = os.environ.get("GEMINI_API_KEY", "")
        if not chave:
            raise ServicoErro("Gemini: GEMINI_API_KEY não configurada.")
        modelo = os.environ.get("GEMINI_MODEL", MODELO_PADRAO)
        dados = post_com_retry(
            "Gemini", f"{URL_BASE}/{modelo}:generateContent", timeout=45,
            headers={"x-goog-api-key": chave},
            json={
                "contents": [{"role": "user", "parts": [{"text": build_prompt(transcricao, campos)}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "responseSchema": _schema(campos),
                },
            },
        )
        try:
            partes = dados["candidates"][0]["content"]["parts"]
            bruto = json.loads("".join(p.get("text", "") for p in partes))
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ServicoErro("Gemini: resposta inválida.") from e
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
