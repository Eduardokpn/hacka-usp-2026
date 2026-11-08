"""POST com novas tentativas e mensagens de erro legíveis (nunca incluem as chaves)."""
from __future__ import annotations

import time

import httpx

TENTATIVAS = 3
ESPERA_MAX_S = 10.0


class ServicoErro(Exception):
    """Falha de um serviço externo, com mensagem pronta para o usuário."""


def _espera(resposta: httpx.Response | None, tentativa: int) -> float:
    if resposta is not None:
        try:
            return min(float(resposta.headers["retry-after"]), ESPERA_MAX_S)
        except (KeyError, ValueError):
            pass
    return float(2 ** tentativa)


def _mensagem(servico: str, status: int) -> str:
    if status in (401, 403):
        return f"{servico}: chave de API inválida ou sem permissão."
    if status == 402:
        return f"{servico}: conta sem saldo."
    if status == 429:
        return f"{servico}: limite de uso excedido. Aguarde e tente novamente."
    return f"{servico}: erro {status} do serviço."


def post_com_retry(servico: str, url: str, timeout: float, **kwargs) -> dict:
    erro = f"{servico}: sem conexão com o serviço."
    for tentativa in range(TENTATIVAS):
        resposta = None
        try:
            resposta = httpx.post(url, timeout=timeout, **kwargs)
        except httpx.TimeoutException:
            erro = f"{servico}: o serviço demorou demais para responder."
        except httpx.TransportError:
            erro = f"{servico}: sem conexão com o serviço."
        else:
            if resposta.is_success:
                try:
                    return resposta.json()
                except ValueError as e:
                    raise ServicoErro(f"{servico}: resposta inválida.") from e
            erro = _mensagem(servico, resposta.status_code)
            if resposta.status_code != 429 and resposta.status_code < 500:
                raise ServicoErro(erro)
        if tentativa < TENTATIVAS - 1:
            time.sleep(_espera(resposta, tentativa))
    raise ServicoErro(erro)
