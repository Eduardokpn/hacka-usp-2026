"""Abre o prontuario.html preenchido, sem gravar dados da consulta em disco (R7, R8).

A página é entregue uma única vez por um servidor local temporário, em um endereço
aleatório acessível só neste computador.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.models import Field

HTML_PATH = Path(__file__).resolve().parents[2] / "prontuario.html"
ESPERA_S = 60
_BLOCO_DADOS = re.compile(r'(<script type="application/json" id="campos">).*?(</script>)', re.S)


class ProntuarioErro(Exception):
    """Não foi possível abrir o prontuário."""


def montar_html(modelo: str, campos: list[Field], valores: dict[str, str]) -> str:
    dados = {"campos": [c.to_dict() for c in campos], "valores": valores}
    # "<" escapado para que nenhum valor consiga fechar a tag <script>.
    texto = json.dumps(dados, ensure_ascii=False).replace("<", "\\u003c")
    return _BLOCO_DADOS.sub(lambda m: m.group(1) + texto + m.group(2), modelo, count=1)


def _servir_uma_vez(pagina: bytes) -> str:
    token = secrets.token_urlsafe(24)
    servido = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        timeout = 5

        def do_GET(self):
            if self.path != f"/{token}" or servido.is_set():
                self.send_error(404)
                return
            servido.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(pagina)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(pagina)

        def log_message(self, *_args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    servidor.daemon_threads = True
    servidor.timeout = 1

    def atender():
        limite = time.monotonic() + ESPERA_S
        while not servido.is_set() and time.monotonic() < limite:
            servidor.handle_request()
        servidor.server_close()

    threading.Thread(target=atender, daemon=True).start()
    return f"http://127.0.0.1:{servidor.server_address[1]}/{token}"


def abrir_prontuario(campos: list[Field], valores: dict[str, str]) -> None:
    try:
        modelo = HTML_PATH.read_text(encoding="utf-8")
        url = _servir_uma_vez(montar_html(modelo, campos, valores).encode("utf-8"))
    except OSError as e:
        raise ProntuarioErro("Não foi possível preparar o prontuário.") from e
    if not webbrowser.open(url):
        raise ProntuarioErro("Não foi possível abrir o navegador.")
