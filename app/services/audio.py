"""Captura do microfone em blocos. O áudio vive só em memória (R7, R8)."""
from __future__ import annotations

import io
import threading
import wave

import numpy as np
import sounddevice as sd

TAXA = 16_000
BLOCO_SEGUNDOS = 5
BLOCO_MAX_SEGUNDOS = 8
_JANELA = int(TAXA * 0.03)  # 30 ms
_SILENCIO_MIN = 150  # RMS em int16
_SILENCIO_RELATIVO = 0.35  # da mediana do trecho, para se adaptar ao microfone
_FALA_MIN = 120  # abaixo disso, em todo o bloco, não há fala


def _rms(amostras: np.ndarray) -> np.ndarray:
    n = len(amostras) // _JANELA
    if n == 0:
        return np.zeros(0)
    janelas = amostras[: n * _JANELA].reshape(n, _JANELA).astype(np.float64)
    return np.sqrt(np.mean(janelas ** 2, axis=1))


def _para_wav(amostras: np.ndarray) -> bytes | None:
    """WAV em memória; None se o trecho não tiver fala."""
    rms = _rms(amostras)
    if rms.size == 0 or rms.max() < _FALA_MIN:
        return None
    saida = io.BytesIO()
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(amostras.tobytes())
    return saida.getvalue()


class Recorder:
    def __init__(self):
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._partes: list[np.ndarray] = []
        self._ativo = False

    def _callback(self, indata, _frames, _time, _status):
        if self._ativo:
            with self._lock:
                self._partes.append(indata[:, 0].copy())

    def start(self) -> None:
        """Abre o microfone. Levanta sd.PortAudioError se não houver dispositivo."""
        self.descartar()
        self._stream = sd.InputStream(
            samplerate=TAXA, channels=1, dtype="int16", callback=self._callback,
        )
        self._ativo = True
        self._stream.start()

    def pause(self) -> None:
        self._ativo = False

    def resume(self) -> None:
        self._ativo = True

    def _fechar(self) -> None:
        self._ativo = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _retirar_tudo(self) -> np.ndarray:
        with self._lock:
            partes, self._partes = self._partes, []
        return np.concatenate(partes) if partes else np.zeros(0, dtype=np.int16)

    def pop_bloco(self) -> bytes | None:
        """Próximo bloco pronto, cortado num silêncio para não partir palavras."""
        amostras = self._retirar_tudo()
        corte = self._ponto_de_corte(amostras)
        if corte is None:
            if amostras.size:
                with self._lock:
                    self._partes.insert(0, amostras)
            return None
        with self._lock:
            self._partes.insert(0, amostras[corte:])
        return _para_wav(amostras[:corte])

    @staticmethod
    def _ponto_de_corte(amostras: np.ndarray) -> int | None:
        minimo = TAXA * BLOCO_SEGUNDOS
        maximo = TAXA * BLOCO_MAX_SEGUNDOS
        if len(amostras) < minimo:
            return None
        rms = _rms(amostras)
        limiar = max(_SILENCIO_MIN, float(np.median(rms)) * _SILENCIO_RELATIVO)
        inicio = minimo // _JANELA
        silencios = np.flatnonzero(rms[inicio:maximo // _JANELA] < limiar)
        if silencios.size:
            return (inicio + int(silencios[0])) * _JANELA
        return maximo if len(amostras) >= maximo else None

    def finalizar(self) -> bytes | None:
        """Fecha o microfone e devolve o último trecho."""
        self._fechar()
        return _para_wav(self._retirar_tudo())

    def descartar(self) -> None:
        self._fechar()
        with self._lock:
            self._partes = []
