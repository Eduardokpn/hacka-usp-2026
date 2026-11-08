"""Janela principal: alterna entre gravação, configuração e prontuário."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget,
)

from app.models import ConfigStore, Field
from app.session import Session
from app.ui.config_screen import ConfigScreen
from app.ui.record_screen import RecordScreen
from app.ui.review_screen import ReviewScreen
from app.ui.widgets import Toast


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prontuário em copiar e colar")
        self.resize(1100, 760)
        self.setMinimumSize(820, 600)

        self.store = ConfigStore()
        self.campos: list[Field] = self.store.load()
        self.session = Session()

        root = QWidget()
        root.setObjectName("root")
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.stack = QStackedWidget()
        self.record = RecordScreen(self.session, lambda: self.campos)
        self.config = ConfigScreen()
        self.review = ReviewScreen()
        for w in (self.record, self.config, self.review):
            self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.toast = Toast(root)

        self.record.open_config.connect(self._open_config)
        self.record.processed.connect(self._open_review)
        self.config.back.connect(lambda: self._go(self.record))
        self.config.saved.connect(self._save_config)
        self.review.finished.connect(self._finish)
        self.review.copied.connect(lambda nome: self.toast.show_message(f"“{nome}” copiado"))

    # --------------------------------------------------------- navegação
    def _go(self, widget: QWidget):
        self.stack.setCurrentWidget(widget)
        fx = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", widget)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start()
        if widget is self.record:
            self.record.refresh()

    def _open_config(self):
        self.config.load(self.campos)
        self._go(self.config)

    def _save_config(self, campos: list[Field]):
        self.campos = campos
        self.store.save(campos)
        self._go(self.record)
        self.toast.show_message("Configuração salva")

    def _open_review(self):
        self.review.load(self.campos, self.session.valores, self.session.transcricao)
        self._go(self.review)

    def _finish(self):
        self.review.clear()
        self.record.reset()
        self._go(self.record)
        box = QMessageBox(self)
        box.setWindowTitle("Consulta encerrada")
        box.setIcon(QMessageBox.Information)
        box.setText("<b>Nada desta consulta ficou guardado neste computador.</b>")
        box.setInformativeText(
            "O áudio, a transcrição e os campos preenchidos foram apagados.\n\n"
            "Para gerar o prontuário, o áudio foi enviado à Groq e a transcrição ao Google (Gemini)."
        )
        box.exec()

    def closeEvent(self, e):
        self.record.shutdown()
        self.review.clear()
        self.session.limpar()
        super().closeEvent(e)
