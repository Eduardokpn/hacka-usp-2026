"""Configuração de campos (F1, R2). Protótipo: páginas 3 e 4 do PDF."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from app.models import Configuracao, Field, FieldType, Template

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
    saved = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("screen")
        self.rows: list[_FieldRow] = []
        self.dirty = False
        self.templates: list[Template] = []
        self.ativo = ""
        self._idx = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 24)
        root.setSpacing(6)

        title = QLabel("Configuração")
        title.setObjectName("h1")
        root.addWidget(title)
        sub = QLabel("Crie um template para cada tipo de atendimento. A descrição de cada campo orienta a interpretação da consulta.")
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        root.addWidget(sub)
        root.addSpacing(12)

        # templates
        barra = QHBoxLayout()
        barra.setSpacing(4)
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.currentChanged.connect(self._on_tab)
        barra.addWidget(self.tabs, 1)
        self.btn_novo = self._acao("Novo", self._novo)
        self.btn_duplicar = self._acao("Duplicar", self._duplicar)
        self.btn_renomear = self._acao("Renomear", self._renomear)
        self.btn_excluir = self._acao("Excluir", self._excluir)
        for b in (self.btn_novo, self.btn_duplicar, self.btn_renomear, self.btn_excluir):
            barra.addWidget(b, 0, Qt.AlignVCenter)
        root.addLayout(barra)
        root.addSpacing(12)

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
        self.btn_save = QPushButton("Salvar e usar este template")
        self.btn_save.setObjectName("primary")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)
        foot.addWidget(self.btn_back)
        foot.addWidget(self.btn_save)
        root.addLayout(foot)

    def _acao(self, texto, fn) -> QPushButton:
        b = QPushButton(texto)
        b.setObjectName("link")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(fn)
        return b

    # -------------------------------------------------------- templates
    def load(self, config: Configuracao):
        """Abre uma cópia de trabalho: nada muda até salvar."""
        self.templates = [Template(t.nome, list(t.campos)) for t in config.templates]
        self.ativo = config.ativo
        self._idx = [t.nome for t in self.templates].index(config.ativo)
        self._montar_abas()
        self._mostrar(self._idx)
        self.dirty = False

    def _montar_abas(self):
        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for t in self.templates:
            self.tabs.addTab(f"{t.nome}  (em uso)" if t.nome == self.ativo else t.nome)
        self.tabs.setCurrentIndex(self._idx)
        self.tabs.blockSignals(False)
        self.btn_excluir.setEnabled(len(self.templates) > 1)

    def _mostrar(self, i: int):
        for r in self.rows:
            r.setParent(None)
            r.deleteLater()
        self.rows = []
        for c in self.templates[i].campos:
            self._insert_row(_FieldRow(c))
        self.error.clear()
        self._sync()
        self.scroll.verticalScrollBar().setValue(0)

    def _guardar_aba(self) -> bool:
        """Copia as linhas para o template aberto; False se houver campo inválido."""
        campos = self._validate()
        if campos is None:
            return False
        self.templates[self._idx].campos = campos
        return True

    def _on_tab(self, i: int):
        if i == self._idx:
            return
        if not self._guardar_aba():
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(self._idx)
            self.tabs.blockSignals(False)
            return
        self._idx = i
        self._mostrar(i)

    def _pedir_nome(self, titulo: str, sugestao: str = "", atual: str | None = None) -> str | None:
        nome, ok = QInputDialog.getText(self, titulo, "Nome do template:", text=sugestao)
        nome = nome.strip()
        if not ok:
            return None
        if not nome:
            self.error.setText("O template precisa de um nome.")
            return None
        existentes = {t.nome.casefold() for t in self.templates if t.nome != atual}
        if nome.casefold() in existentes:
            self.error.setText(f"Já existe um template chamado “{nome}”.")
            return None
        return nome

    def _adicionar(self, nome: str, campos: list[Field]):
        self.templates.append(Template(nome, campos))
        self._idx = len(self.templates) - 1
        self._montar_abas()
        self._mostrar(self._idx)
        self._mark_dirty()

    def _novo(self):
        if self._guardar_aba() and (nome := self._pedir_nome("Novo template")):
            self._adicionar(nome, [])

    def _duplicar(self):
        if not self._guardar_aba():
            return
        origem = self.templates[self._idx]
        if nome := self._pedir_nome("Duplicar template", f"{origem.nome} (cópia)"):
            self._adicionar(nome, list(origem.campos))

    def _renomear(self):
        template = self.templates[self._idx]
        nome = self._pedir_nome("Renomear template", template.nome, atual=template.nome)
        if nome and nome != template.nome:
            if self.ativo == template.nome:
                self.ativo = nome
            template.nome = nome
            self._montar_abas()
            self._mark_dirty()

    def _excluir(self):
        template = self.templates[self._idx]
        resp = QMessageBox.question(
            self, "Excluir template",
            f"Excluir o template “{template.nome}” e todos os seus campos?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        del self.templates[self._idx]
        self._idx = min(self._idx, len(self.templates) - 1)
        if self.ativo == template.nome:
            self.ativo = self.templates[0].nome
        self._montar_abas()
        self._mostrar(self._idx)
        self._mark_dirty()

    # ------------------------------------------------------------ lista

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
        if not self._guardar_aba():
            return
        self.dirty = False
        self.saved.emit(Configuracao(self.templates, self.templates[self._idx].nome))

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
