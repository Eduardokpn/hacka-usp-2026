"""Prontuário em copiar e colar — MVP de demonstração (transcrição e interpretação simuladas).

Uso: python main.py
"""
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import QSS


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Prontuário em copiar e colar")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
