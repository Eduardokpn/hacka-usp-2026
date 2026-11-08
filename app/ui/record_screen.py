"""Tela de gravação (F2, F3). Protótipo: páginas 1, 2 e 5 do PDF."""
from __future__ import annotations

import os
import queue

import sounddevice as sd
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

from app.models import Field
from app.services.audio import Recorder
from app.services.http import ServicoErro
from app.services.interpreter import GeminiInterpreter
from app.services.transcriber import GroqTranscriber
from app.session import Estado, Session
from app.ui import theme
from app.ui.widgets import CircleButton, IconButton, Spinner


class _TranscribeWorker(QObject):
    """Transcreve os blocos um a um, na ordem em que foram gravados."""
    texto = Signal(int, str)
    falhou = Signal(int, str)
    fim = Signal(int)

    def __init__(self):
        super().__init__()
        self.fila: queue.Queue = queue.Queue()
        self.transcriber = GroqTranscriber()

    def run(self):
        while (item := self.fila.get()) is not None:
            token, wav = item
            if wav is None:
                self.fim.emit(token)
                continue
            try:
                texto = self.transcriber.transcrever(wav)
            except ServicoErro as e:
                self.falhou.emit(token, str(e))
            else:
                if texto:
                    self.texto.emit(token, texto)


class _InterpretWorker(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, token: int, transcricao: str, campos: list[Field]):
        super().__init__()
        self.token = token
        self.transcricao = transcricao
        self.campos = campos

    def run(self):
        try:
            valores = GeminiInterpreter().interpretar(self.transcricao, self.campos)
        except ServicoErro as e:
            self.failed.emit(self.token, str(e))
        else:
            self.done.emit(self.token, valores)


def _labeled(button: QWidget, text: str) -> tuple[QWidget, QLabel]:
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(button, 0, Qt.AlignHCenter)
    lbl = QLabel(text)
    lbl.setObjectName("hint")
    lbl.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl)
    return box, lbl


class RecordScreen(QWidget):
    open_config = Signal()
    processed = Signal()

    def __init__(self, session: Session, get_campos, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.session = session
        self.get_campos = get_campos
        self.recorder = Recorder()
        self._token = 0  # respostas de consultas já descartadas são ignoradas
        self._falhas = 0
        self._thread: QThread | None = None

        self._tr_thread = QThread(self)
        self._tr_worker = _TranscribeWorker()
        self._tr_worker.moveToThread(self._tr_thread)
        self._tr_thread.started.connect(self._tr_worker.run)
        self._tr_worker.texto.connect(self._on_bloco)
        self._tr_worker.falhou.connect(self._on_bloco_falhou)
        self._tr_worker.fim.connect(self._on_transcrito)
        self._tr_thread.start()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)

        # barra superior
        top = QHBoxLayout()
        self.btn_config = IconButton("sliders", 44)
        self.btn_config.setToolTip("Configurar campos")
        self.btn_config.clicked.connect(self.open_config.emit)
        top.addWidget(self.btn_config)
        brand = QLabel("PRONTUÁRIO EM COPIAR E COLAR")
        brand.setObjectName("eyebrow")
        top.addSpacing(8)
        top.addWidget(brand)
        top.addStretch()
        root.addLayout(top)

        root.addStretch(2)

        # status e cronômetro
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)
        self.timer_lbl = QLabel("00:00")
        self.timer_lbl.setObjectName("timer")
        self.timer_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self.timer_lbl)
        root.addSpacing(18)

        # botões
        row = QHBoxLayout()
        row.setSpacing(36)
        row.addStretch()
        self.btn_cancel = CircleButton(theme.RED, "x", 78)
        self.btn_cancel.setToolTip("Interromper e descartar")
        self.btn_main = CircleButton(theme.DARK, "mic", 104)
        self.btn_done = CircleButton(theme.GREEN, "check", 78)
        self.btn_done.setToolTip("Finalizar consulta")
        box_c, _ = _labeled(self.btn_cancel, "Interromper")
        box_m, self.main_hint = _labeled(self.btn_main, "Gravar")
        box_d, _ = _labeled(self.btn_done, "Finalizar")
        for b in (box_c, box_m, box_d):
            row.addWidget(b, 0, Qt.AlignVCenter)
        row.addStretch()
        root.addLayout(row)

        self.btn_cancel.clicked.connect(self._interromper)
        self.btn_main.clicked.connect(self._toggle)
        self.btn_done.clicked.connect(self._finalizar)

        # aviso / processamento
        root.addSpacing(14)
        self.warn = QLabel("Configure ao menos um campo antes de gravar.")
        self.warn.setObjectName("warn")
        self.warn.setAlignment(Qt.AlignCenter)
        warn_row = QHBoxLayout()
        warn_row.addStretch()
        warn_row.addWidget(self.warn)
        warn_row.addStretch()
        root.addLayout(warn_row)

        proc_row = QHBoxLayout()
        proc_row.addStretch()
        self.spinner = Spinner()
        self.spinner.hide()
        proc_row.addWidget(self.spinner)
        proc_row.addStretch()
        root.addLayout(proc_row)

        root.addStretch(1)

        # transcrição parcial
        self.transcript = QFrame()
        self.transcript.setObjectName("transcript")
        tl = QVBoxLayout(self.transcript)
        tl.setContentsMargins(18, 12, 18, 12)
        head = QLabel("TRANSCRIÇÃO EM BLOCOS")
        head.setObjectName("eyebrow")
        tl.addWidget(head)
        self.transcript_text = QPlainTextEdit()
        self.transcript_text.setObjectName("transcriptText")
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setFixedHeight(120)
        tl.addWidget(self.transcript_text)
        root.addWidget(self.transcript)

        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

        self.refresh()

    # ------------------------------------------------------------ estado
    def refresh(self):
        e = self.session.estado
        tem_campos = bool(self.get_campos())
        self.btn_config.setEnabled(e == Estado.OCIOSO)
        self.btn_main.setEnabled(e in (Estado.GRAVANDO, Estado.PAUSADO) or (e == Estado.OCIOSO and tem_campos))
        self.btn_cancel.setEnabled(e in (Estado.GRAVANDO, Estado.PAUSADO))
        self.btn_done.setEnabled(e in (Estado.GRAVANDO, Estado.PAUSADO))
        self.warn.setVisible(e == Estado.OCIOSO and not tem_campos)
        self.transcript.setVisible(e in (Estado.GRAVANDO, Estado.PAUSADO, Estado.PROCESSANDO))

        icon, hint, status = {
            Estado.OCIOSO: ("mic", "Gravar", "Pronto para gravar"),
            Estado.GRAVANDO: ("pause", "Pausar", "● Gravando"),
            Estado.PAUSADO: ("play", "Retomar", "Pausado"),
            Estado.PROCESSANDO: ("mic", "Gravar", "Processando…"),
            Estado.REVISAO: ("mic", "Gravar", ""),
        }[e]
        self.btn_main.set_icon(icon)
        self.btn_main.set_pulsing(e == Estado.GRAVANDO)
        self.btn_main.setToolTip(hint)
        self.main_hint.setText(hint)
        self.status.setText(status)
        color = theme.RED if e == Estado.GRAVANDO else theme.SEC
        self.status.setStyleSheet(f"color:{color}; font-weight:{600 if e == Estado.GRAVANDO else 400};")
        s = self.session.segundos
        self.timer_lbl.setText(f"{s // 60:02d}:{s % 60:02d}")
        self.timer_lbl.setStyleSheet(f"color:{theme.MUTED if e == Estado.PAUSADO else theme.INK};")

    # ------------------------------------------------------------ ações
    def _toggle(self):
        e = self.session.estado
        if e == Estado.OCIOSO:
            self._iniciar()
            return
        if e == Estado.GRAVANDO:
            self.recorder.pause()
            self.session.estado = Estado.PAUSADO
        elif e == Estado.PAUSADO:
            self.recorder.resume()
            self.session.estado = Estado.GRAVANDO
        self.refresh()

    def _iniciar(self):
        faltando = [k for k in ("GROQ_API_KEY", "GEMINI_API_KEY") if not os.environ.get(k)]
        if faltando:
            QMessageBox.warning(self, "Chaves de API", f"Configure no arquivo .env: {', '.join(faltando)}.")
            return
        self.session.limpar()
        self.transcript_text.clear()
        self._token += 1
        self._falhas = 0
        try:
            self.recorder.start()
        except (sd.PortAudioError, OSError):
            QMessageBox.warning(self, "Microfone", "Não foi possível acessar o microfone.")
            return
        self.session.estado = Estado.GRAVANDO
        self._tick.start()
        self.refresh()

    def _on_tick(self):
        if self.session.estado != Estado.GRAVANDO:
            return
        self.session.segundos += 1
        self._enfileirar(self.recorder.pop_bloco())
        self.refresh()

    def _enfileirar(self, wav: bytes | None):
        if wav:
            self._tr_worker.fila.put((self._token, wav))

    def _on_bloco(self, token: int, texto: str):
        if token == self._token:
            self._add_bloco(texto)

    def _on_bloco_falhou(self, token: int, mensagem: str):
        if token == self._token:
            self._falhas += 1
            self.transcript_text.appendPlainText(f"[Trecho não transcrito. {mensagem}]")

    def _add_bloco(self, texto: str):
        self.session.blocos.append(texto)
        self.transcript_text.appendPlainText(texto)
        sb = self.transcript_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _interromper(self):
        anterior = self.session.estado
        self.recorder.pause()
        self.session.estado = Estado.PAUSADO
        self.refresh()
        resp = QMessageBox.question(
            self, "Interromper consulta",
            "Interromper a gravação?\n\nO áudio e a transcrição desta consulta serão apagados "
            "e nada será processado.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self.reset()
        else:
            self.session.estado = anterior
            if anterior == Estado.GRAVANDO:
                self.recorder.resume()
            self.refresh()

    def _finalizar(self):
        self._tick.stop()
        self.session.estado = Estado.PROCESSANDO
        self._enfileirar(self.recorder.finalizar())
        self._tr_worker.fila.put((self._token, None))  # marca o fim da consulta
        self.refresh()
        self.status.setText("Transcrevendo o último trecho…")
        self.spinner.start()

    def _on_transcrito(self, token: int):
        if token != self._token or self.session.estado != Estado.PROCESSANDO:
            return
        if self._falhas:
            QMessageBox.warning(
                self, "Transcrição incompleta",
                f"{self._falhas} trecho(s) da consulta não foram transcritos. "
                "Confira os campos com atenção.",
            )
        self._interpretar()

    def _interpretar(self):
        self.status.setText("Interpretando a consulta…")
        self._thread = QThread(self)
        self._worker = _InterpretWorker(self._token, self.session.transcricao, list(self.get_campos()))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_interpretado)
        self._worker.failed.connect(self._on_interpretacao_falhou)
        self._worker.done.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_interpretado(self, token: int, valores: dict):
        if token != self._token or self.session.estado != Estado.PROCESSANDO:
            return  # sessão foi descartada no meio (ex.: janela fechada)
        self.spinner.stop()
        self.session.valores = valores
        self.session.estado = Estado.REVISAO
        self.processed.emit()

    def _on_interpretacao_falhou(self, token: int, mensagem: str):
        if token != self._token or self.session.estado != Estado.PROCESSANDO:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Não foi possível preencher os campos")
        box.setIcon(QMessageBox.Warning)
        box.setText(mensagem)
        box.setInformativeText("A transcrição foi mantida.")
        repetir = box.addButton("Tentar novamente", QMessageBox.AcceptRole)
        box.addButton("Preencher manualmente", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is repetir:
            self._interpretar()
        else:
            self._on_interpretado(token, {})

    def reset(self):
        """Volta ao ocioso, sem nada da consulta em memória."""
        self._tick.stop()
        self.spinner.stop()
        self._token += 1
        self.recorder.descartar()
        self.session.limpar()
        self.transcript_text.clear()
        self.refresh()

    def shutdown(self):
        self._tick.stop()
        self._token += 1
        self.recorder.descartar()
        self._tr_worker.fila.put(None)
        self._tr_thread.quit()
        self._tr_thread.wait(3000)
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)

    def tem_requisicao_em_andamento(self) -> bool:
        return self._tr_thread.isRunning() or bool(self._thread and self._thread.isRunning())
