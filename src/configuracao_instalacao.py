"""Configuração local, não versionada, para recursos específicos do computador."""

import json
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_CONFIGURACAO = RAIZ_PROJETO / "configuracao_local.json"
PADRAO = {
    "sincronizacao_nuvem_ativa": False,
    "modo_instalacao": "ESCRITA",
    "pasta_google_drive": "",
}


def carregar_configuracao():
    configuracao = dict(PADRAO)
    if ARQUIVO_CONFIGURACAO.is_file():
        try:
            dados = json.loads(ARQUIVO_CONFIGURACAO.read_text(encoding="utf-8"))
            if isinstance(dados, dict):
                configuracao.update(dados)
        except (OSError, json.JSONDecodeError):
            configuracao["erro_configuracao"] = "O arquivo configuracao_local.json é inválido."
    configuracao["sincronizacao_nuvem_ativa"] = configuracao.get("sincronizacao_nuvem_ativa") is True
    modo = str(configuracao.get("modo_instalacao", "ESCRITA")).upper()
    configuracao["modo_instalacao"] = modo if modo in {"ESCRITA", "LEITURA"} else "ESCRITA"
    return configuracao


def somente_leitura():
    config = carregar_configuracao()
    return config["sincronizacao_nuvem_ativa"] and config["modo_instalacao"] == "LEITURA"
