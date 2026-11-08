"""Tela de gravação (F2, F3). Protótipo: páginas 1, 2 e 5 do PDF."""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

from app.models import Field
from app.services.interpreter import MockInterpreter
from app.services.transcriber import BLOCO_SEGUNDOS, MockTranscriber
from app.session import Estado, Session
from app.ui import theme
from app.ui.widgets import CircleButton, IconButton, Spinner


class _InterpretWorker(QObject):
    done = Signal(dict)

    def __init__(self, transcricao: str, campos: list[Field]):
        super().__init__()
        self.transcricao = transcricao
        self.campos = campos

    def run(self):
        self.done.emit(MockInterpreter().interpretar(self.transcricao, self.campos))


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
        self.transcriber = MockTranscriber()
        self._thread: QThread | None = None

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
        head = QLabel("TRANSCRIÇÃO EM BLOCOS · SIMULADA")
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
            self.session.limpar()
            self.transcriber.reset()
            self.transcript_text.clear()
            self.session.estado = Estado.GRAVANDO
            self._tick.start()
        elif e == Estado.GRAVANDO:
            self.session.estado = Estado.PAUSADO
        elif e == Estado.PAUSADO:
            self.session.estado = Estado.GRAVANDO
        self.refresh()

    def _on_tick(self):
        if self.session.estado != Estado.GRAVANDO:
            return
        self.session.segundos += 1
        if self.session.segundos % BLOCO_SEGUNDOS == 0:
            bloco = self.transcriber.transcrever_bloco()
            if bloco:
                self._add_bloco(bloco)
        self.refresh()

    def _add_bloco(self, texto: str):
        self.session.blocos.append(texto)
        self.transcript_text.appendPlainText(texto)
        sb = self.transcript_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _interromper(self):
        anterior = self.session.estado
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
            self.refresh()

    def _finalizar(self):
        self._tick.stop()
        self.session.estado = Estado.PROCESSANDO
        for bloco in self.transcriber.transcrever_restante():
            self._add_bloco(bloco)
        self.refresh()
        self.status.setText("Transcrevendo o último trecho e interpretando a consulta…")
        self.spinner.start()

        self._thread = QThread(self)
        self._worker = _InterpretWorker(self.session.transcricao, list(self.get_campos()))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_interpretado)
        self._worker.done.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_interpretado(self, valores: dict):
        self.spinner.stop()
        if self.session.estado != Estado.PROCESSANDO:
            return  # sessão foi descartada no meio (ex.: janela fechada)
        self.session.valores = valores
        self.session.estado = Estado.REVISAO
        self.processed.emit()

    def reset(self):
        """Volta ao ocioso, sem nada da consulta em memória."""
        self._tick.stop()
        self.spinner.stop()
        self.session.limpar()
        self.transcriber.reset()
        self.transcript_text.clear()
        self.refresh()

    def shutdown(self):
        self._tick.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
