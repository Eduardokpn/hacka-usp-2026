"""Transcrição de cada bloco de áudio com whisper-large-v3-turbo, na Groq."""
from __future__ import annotations

import os

from app.services.http import ServicoErro, post_com_retry

URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODELO = "whisper-large-v3-turbo"


class GroqTranscriber:
    def transcrever(self, wav: bytes) -> str:
        chave = os.environ.get("GROQ_API_KEY", "")
        if not chave:
            raise ServicoErro("Groq: GROQ_API_KEY não configurada.")
        dados = post_com_retry(
            "Groq", URL, timeout=30,
            headers={"Authorization": f"Bearer {chave}"},
            files={"file": ("bloco.wav", wav, "audio/wav")},
            data={"model": MODELO, "language": "pt", "temperature": "0", "response_format": "json"},
        )
        return str(dados.get("text", "")).strip()
