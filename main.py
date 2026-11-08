"""Prontuário em copiar e colar — transcrição pela Groq e preenchimento dos campos pelo Gemini.

Uso: python main.py (chaves no arquivo .env)
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import QSS


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    app = QApplication(sys.argv)
    app.setApplicationName("Prontuário em copiar e colar")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    codigo = app.exec()
    if win.record.tem_requisicao_em_andamento():
        # Destruir um QThread ativo derruba o Python; só aqui a saída é forçada.
        os._exit(codigo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
