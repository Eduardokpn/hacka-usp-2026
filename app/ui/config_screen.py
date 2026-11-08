"""Configuração de campos (F1, R2). Protótipo: páginas 3 e 4 do PDF."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QToolButton, QVBoxLayout, QWidget,
)

from app.models import Field, FieldType

COL_NOME, COL_DESC, COL_TIPO = 3, 5, 2  # proporções das colunas
ACOES_W = 104


class _FieldRow(QFrame):
    changed = Signal()
    move = Signal(object, int)
    remove = Signal(object)

    def __init__(self, campo: Field | None = None):
        super().__init__()
        self.setObjectName("row")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 8, 8)
        lay.setSpacing(10)

        self.nome = QLineEdit()
        self.nome.setPlaceholderText("Ex.: Queixa principal")
        self.desc = QLineEdit()
        self.desc.setPlaceholderText("O que este campo deve receber")
        self.tipo = QComboBox()
        for t in FieldType:
            self.tipo.addItem(t.rotulo, t.value)

        if campo:
            self.nome.setText(campo.nome)
            self.desc.setText(campo.contexto)
            self.tipo.setCurrentIndex(list(FieldType).index(campo.tipo))

        lay.addWidget(self.nome, COL_NOME)
        lay.addWidget(self.desc, COL_DESC)
        lay.addWidget(self.tipo, COL_TIPO)

        acoes = QWidget()
        acoes.setFixedWidth(ACOES_W)
        al = QHBoxLayout(acoes)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(2)
        self.up = self._btn("↑", "Subir", "rowbtn", lambda: self.move.emit(self, -1))
        self.down = self._btn("↓", "Descer", "rowbtn", lambda: self.move.emit(self, 1))
        self.dele = self._btn("✕", "Remover", "delbtn", lambda: self.remove.emit(self))
        for b in (self.up, self.down, self.dele):
            al.addWidget(b)
        lay.addWidget(acoes)

        self.nome.textChanged.connect(self._on_change)
        self.desc.textChanged.connect(self._on_change)
        self.tipo.currentIndexChanged.connect(self._on_change)

    def _btn(self, text, tip, name, fn):
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setObjectName(name)
        b.setFixedSize(32, 32)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(fn)
        return b

    def _on_change(self):
        self.set_error(False)
        self.changed.emit()

    def set_error(self, on: bool):
        self.setProperty("erro", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def to_field(self) -> Field:
        return Field(self.nome.text().strip(), self.desc.text().strip(), FieldType(self.tipo.currentData()))


class ConfigScreen(QWidget):
    back = Signal()
    saved = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.rows: list[_FieldRow] = []
        self.dirty = False

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 24)
        root.setSpacing(6)

        title = QLabel("Configuração")
        title.setObjectName("h1")
        root.addWidget(title)
        sub = QLabel("Defina os campos do prontuário. O contexto de cada campo orienta a interpretação da consulta.")
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        root.addWidget(sub)
        root.addSpacing(16)

        # cabeçalho das colunas
        head = QHBoxLayout()
        head.setContentsMargins(11, 0, 9, 0)
        head.setSpacing(10)
        for text, stretch in (("NOME", COL_NOME), ("DESCRIÇÃO", COL_DESC), ("TIPO", COL_TIPO)):
            lbl = QLabel(text)
            lbl.setObjectName("colhead")
            head.addWidget(lbl, stretch)
        spacer = QWidget()
        spacer.setFixedWidth(ACOES_W)
        head.addWidget(spacer)
        root.addLayout(head)

        # lista
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        inner = QWidget()
        self.list_lay = QVBoxLayout(inner)
        self.list_lay.setContentsMargins(0, 4, 0, 4)
        self.list_lay.setSpacing(8)

        self.empty = QLabel("Nenhum campo ainda. Comece inserindo o primeiro.")
        self.empty.setObjectName("sub")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setMinimumHeight(70)
        self.list_lay.addWidget(self.empty)

        self.add_btn = QPushButton("+  Inserir configuração")
        self.add_btn.setObjectName("ghost")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_new)
        self.list_lay.addWidget(self.add_btn)
        self.list_lay.addStretch()
        self.scroll.setWidget(inner)
        root.addWidget(self.scroll, 1)

        # rodapé
        self.error = QLabel()
        self.error.setObjectName("error")
        root.addWidget(self.error)
        foot = QHBoxLayout()
        foot.addStretch()
        self.btn_back = QPushButton("Voltar")
        self.btn_back.setObjectName("secondary")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_save = QPushButton("Salvar configuração")
        self.btn_save.setObjectName("primary")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)
        foot.addWidget(self.btn_back)
        foot.addWidget(self.btn_save)
        root.addLayout(foot)

    # ------------------------------------------------------------ lista
    def load(self, campos: list[Field]):
        for r in self.rows:
            r.setParent(None)
            r.deleteLater()
        self.rows = []
        for c in campos:
            self._insert_row(_FieldRow(c))
        self.error.clear()
        self.dirty = False
        self._sync()

    def _insert_row(self, row: _FieldRow):
        row.changed.connect(self._mark_dirty)
        row.move.connect(self._move)
        row.remove.connect(self._remove)
        self.rows.append(row)
        self._relayout()

    def _add_new(self):
        row = _FieldRow()
        self._insert_row(row)
        self._mark_dirty()
        row.nome.setFocus()
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(60, lambda: bar.setValue(bar.maximum()))

    def _move(self, row: _FieldRow, delta: int):
        i = self.rows.index(row)
        j = i + delta
        if 0 <= j < len(self.rows):
            self.rows[i], self.rows[j] = self.rows[j], self.rows[i]
            self._relayout()
            self._mark_dirty()

    def _remove(self, row: _FieldRow):
        self.rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._relayout()
        self._mark_dirty()

    def _relayout(self):
        for r in self.rows:
            self.list_lay.removeWidget(r)
        for i, r in enumerate(self.rows):
            self.list_lay.insertWidget(1 + i, r)
            r.up.setEnabled(i > 0)
            r.down.setEnabled(i < len(self.rows) - 1)
        self._sync()

    def _sync(self):
        self.empty.setVisible(not self.rows)

    def _mark_dirty(self):
        self.dirty = True
        self.error.clear()

    # ------------------------------------------------------------ ações
    def _validate(self) -> list[Field] | None:
        campos = [r.to_field() for r in self.rows]
        vistos: dict[str, int] = {}
        msg = None
        for i, (r, c) in enumerate(zip(self.rows, campos)):
            chave = c.nome.casefold()
            if not c.nome:
                r.set_error(True)
                msg = msg or "Todo campo precisa de um nome."
            elif chave in vistos:
                r.set_error(True)
                self.rows[vistos[chave]].set_error(True)
                msg = msg or f"O nome “{c.nome}” está repetido. Cada campo precisa de um nome único."
            else:
                vistos[chave] = i
        if msg:
            self.error.setText(msg)
            return None
        return campos

    def _on_save(self):
        campos = self._validate()
        if campos is None:
            return
        self.dirty = False
        self.saved.emit(campos)

    def _on_back(self):
        if self.dirty:
            resp = QMessageBox.question(
                self, "Alterações não salvas",
                "Há alterações não salvas na configuração. Descartar?",
                QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel,
            )
            if resp != QMessageBox.Discard:
                return
        self.back.emit()
