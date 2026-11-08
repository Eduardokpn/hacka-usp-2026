"""Transcrição mockada. No futuro: whisper-large-v3-turbo local, em blocos (D13)."""
from __future__ import annotations

ROTEIRO = [
    "Médico: Bom dia, o que traz a senhora aqui hoje?",
    "Paciente: Doutor, estou com dor de cabeça e febre há três dias.",
    "Médico: A dor começou de repente ou foi aumentando?",
    "Paciente: Foi aumentando. No segundo dia veio a febre e uma dor no corpo.",
    "Médico: Teve tosse, dor de garganta ou falta de ar?",
    "Paciente: Um pouco de dor de garganta, tosse não.",
    "Médico: A senhora fuma?",
    "Paciente: Fumo sim, uns dez cigarros por dia.",
    "Médico: Tem alergia a algum remédio?",
    "Paciente: Tenho alergia a dipirona.",
    "Médico: Vou aferir os sinais. Frequência cardíaca 88, temperatura 37,8, pressão 120 por 80.",
    "Médico: Saturação 97 por cento. Orofaringe com hiperemia leve, sem exsudato.",
    "Médico: Peso 68 quilos.",
    "Médico: Vamos tratar como quadro viral, com repouso e hidratação.",
]

BLOCO_SEGUNDOS = 5


class MockTranscriber:
    """Devolve a próxima fala do roteiro a cada bloco de áudio."""

    def __init__(self):
        self._i = 0

    def reset(self) -> None:
        self._i = 0

    def transcrever_bloco(self) -> str | None:
        if self._i >= len(ROTEIRO):
            return None
        texto = ROTEIRO[self._i]
        self._i += 1
        return texto

    def transcrever_restante(self) -> list[str]:
        """Último trecho ao finalizar (F3.1)."""
        if self._i < len(ROTEIRO):
            texto = self.transcrever_bloco()
            return [texto] if texto else []
        return []
