"""Revisar e copiar (F4) e encerrar (F5). Protótipo: página 6 do PDF."""
from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.models import Field, FieldType
from app.services.interpreter import formatar_valor
from app.services.prontuario import ProntuarioErro, abrir_prontuario
from app.ui import theme
from app.ui.widgets import IconButton

CHECK_OPCOES = [("— não mencionado", None), ("Sim", True), ("Não", False)]


class _FieldCard(QFrame):
    copied = Signal(str)

    def __init__(self, campo: Field, valor):
        super().__init__()
        self.campo = campo
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 14, 16)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        nome = QLabel(campo.nome)
        nome.setObjectName("fieldname")
        head.addWidget(nome)
        chip = QLabel(campo.tipo.rotulo)
        chip.setObjectName("chip")
        head.addWidget(chip)
        self.empty_tag = QLabel("Não mencionado na consulta")
        self.empty_tag.setObjectName("emptytag")
        head.addWidget(self.empty_tag)
        head.addStretch()
        lay.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(10)
        self.editor = self._make_editor(valor)
        estreito = campo.tipo in (FieldType.INTEIRO, FieldType.DECIMAL, FieldType.CHECKBOX)
        body.addWidget(self.editor, 0 if estreito else 1)
        self.copy_btn = IconButton("copy", 40, theme.SEC)
        self.copy_btn.setToolTip("Copiar este campo")
        self.copy_btn.clicked.connect(self._copy)
        body.addWidget(self.copy_btn, 0, Qt.AlignTop)
        if estreito:
            self.editor.setFixedWidth(240)
            body.addStretch(1)
        lay.addLayout(body)

        self._update_empty()

    def _make_editor(self, valor):
        t = self.campo.tipo
        texto = formatar_valor(t, valor)
        if t == FieldType.TEXTO_LONGO:
            ed = QPlainTextEdit(texto)
            ed.setPlaceholderText("Vazio — preencha se necessário")
            ed.setFixedHeight(110)
            ed.textChanged.connect(self._update_empty)
            return ed
        if t == FieldType.CHECKBOX:
            ed = QComboBox()
            for rot, v in CHECK_OPCOES:
                ed.addItem(rot, v)
            ed.setCurrentIndex([v for _, v in CHECK_OPCOES].index(valor))
            ed.setMaximumWidth(260)
            ed.currentIndexChanged.connect(self._update_empty)
            return ed
        ed = QLineEdit(texto)
        ed.setPlaceholderText("Vazio — preencha se necessário")
        if t == FieldType.INTEIRO:
            ed.setValidator(QRegularExpressionValidator(QRegularExpression(r"-?\d{0,9}")))
            ed.setMaximumWidth(260)
        elif t == FieldType.DECIMAL:
            ed.setValidator(QRegularExpressionValidator(QRegularExpression(r"-?\d{0,9}([.,]\d{0,4})?")))
            ed.setMaximumWidth(260)
        ed.textChanged.connect(self._update_empty)
        return ed

    def texto_para_copiar(self) -> str:
        t = self.campo.tipo
        if t == FieldType.CHECKBOX:
            return formatar_valor(t, self.editor.currentData())
        if t == FieldType.TEXTO_LONGO:
            return self.editor.toPlainText().strip()
        texto = self.editor.text().strip()
        if t == FieldType.DECIMAL:
            texto = texto.replace(".", ",")
        return texto

    def _update_empty(self):
        vazio = self.texto_para_copiar() == ""
        self.empty_tag.setVisible(vazio)
        self.setProperty("vazio", vazio)
        self.style().unpolish(self)
        self.style().polish(self)

    def _copy(self):
        QGuiApplication.clipboard().setText(self.texto_para_copiar())
        self.copy_btn.set_icon("done", theme.ACCENT)
        QTimer.singleShot(1300, self.copy_btn, lambda: self.copy_btn.set_icon("copy", theme.SEC))
        self.copied.emit(self.campo.nome)


class ReviewScreen(QWidget):
    finished = Signal()
    copied = Signal(str)
    sent = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self._transcricao = ""
        self.cards: list[_FieldCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 24)
        root.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel("Prontuário")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch()
        btn_tr = QPushButton("Ver transcrição")
        btn_tr.setObjectName("link")
        btn_tr.setCursor(Qt.PointingHandCursor)
        btn_tr.clicked.connect(self._show_transcript)
        top.addWidget(btn_tr, 0, Qt.AlignBottom)
        root.addLayout(top)
        sub = QLabel("Revise, ajuste e copie cada campo para o seu sistema de prontuário.")
        sub.setObjectName("sub")
        root.addWidget(sub)
        root.addSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.list_lay = QVBoxLayout(self.inner)
        self.list_lay.setContentsMargins(0, 0, 6, 0)
        self.list_lay.setSpacing(12)
        self.list_lay.addStretch()
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        root.addSpacing(8)
        foot = QHBoxLayout()
        note = QLabel("Ao confirmar, áudio, transcrição e campos desta consulta são apagados.")
        note.setObjectName("hint")
        foot.addWidget(note)
        foot.addStretch()
        enviar = QPushButton("Enviar para o prontuário")
        enviar.setObjectName("secondary")
        enviar.setCursor(Qt.PointingHandCursor)
        enviar.clicked.connect(self._enviar)
        foot.addWidget(enviar)
        ok = QPushButton("OK, concluir consulta")
        ok.setObjectName("primary")
        ok.setCursor(Qt.PointingHandCursor)
        ok.setMinimumWidth(200)
        ok.clicked.connect(self.finished.emit)
        foot.addWidget(ok)
        root.addLayout(foot)

    def load(self, campos: list[Field], valores: dict, transcricao: str):
        self.clear()
        self._transcricao = transcricao
        for i, c in enumerate(campos):
            card = _FieldCard(c, valores.get(c.nome))
            card.copied.connect(self.copied.emit)
            self.cards.append(card)
            self.list_lay.insertWidget(i, card)
        self.scroll.verticalScrollBar().setValue(0)

    def clear(self):
        for c in self.cards:
            c.setParent(None)
            c.deleteLater()
        self.cards = []
        self._transcricao = ""

    def _enviar(self):
        campos = [card.campo for card in self.cards]
        valores = {card.campo.nome: card.texto_para_copiar() for card in self.cards}
        try:
            abrir_prontuario(campos, valores)
        except ProntuarioErro as e:
            QMessageBox.warning(self, "Prontuário", str(e))
        else:
            self.sent.emit()

    def _show_transcript(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Transcrição")
        dlg.resize(620, 440)
        dlg.setStyleSheet(f"background:{theme.SURFACE};")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 16)
        txt = QPlainTextEdit(self._transcricao)
        txt.setReadOnly(True)
        lay.addWidget(txt)
        fechar = QPushButton("Fechar")
        fechar.setObjectName("secondary")
        fechar.clicked.connect(dlg.accept)
        lay.addWidget(fechar, 0, Qt.AlignRight)
        dlg.exec()
        txt.clear()
