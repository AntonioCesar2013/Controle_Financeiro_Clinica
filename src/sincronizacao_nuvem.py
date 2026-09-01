"""Publicação e atualização futura de cópias imutáveis via pasta do Google Drive."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from src import banco
from src.backup_banco import _validar_banco, criar_backup
from src.configuracao_instalacao import carregar_configuracao


def _pasta(configuracao):
    valor = str(configuracao.get("pasta_google_drive") or "").strip()
    if not valor:
        raise ValueError("Configure a pasta sincronizada do Google Drive.")
    return Path(valor).expanduser().resolve()


def obter_status():
    config = carregar_configuracao()
    pasta = str(config.get("pasta_google_drive") or "")
    versoes = []
    if pasta and Path(pasta).is_dir():
        versoes = sorted(Path(pasta).glob("clinica_versao_*.db"), reverse=True)
    return {
        "ativa": config["sincronizacao_nuvem_ativa"],
        "modo": config["modo_instalacao"],
        "pasta_google_drive": pasta,
        "ultima_versao": versoes[0].name if versoes else None,
        "quantidade_versoes": len(versoes),
        "preparada": True,
        "mensagem": "Infraestrutura preparada e desativada por padrão.",
    }


def publicar_versao():
    config = carregar_configuracao()
    if not config["sincronizacao_nuvem_ativa"]:
        return {"sucesso": False, "erro": "A sincronização com a nuvem está desativada."}
    if config["modo_instalacao"] != "ESCRITA":
        return {"sucesso": False, "erro": "Somente a instalação principal pode publicar versões."}
    pasta = _pasta(config)
    pasta.mkdir(parents=True, exist_ok=True)
    identificador = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destino = pasta / f"clinica_versao_{identificador}.db"
    temporario = pasta / f".{destino.name}.tmp"
    origem = banco.conectar()
    copia = sqlite3.connect(temporario)
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()
    _validar_banco(temporario)
    os.replace(temporario, destino)
    manifesto = pasta / "versao_atual.json"
    manifesto_tmp = pasta / ".versao_atual.json.tmp"
    manifesto_tmp.write_text(json.dumps({"arquivo": destino.name, "publicada_em": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(manifesto_tmp, manifesto)
    return {"sucesso": True, "arquivo": destino.name}


def atualizar_versao_local():
    config = carregar_configuracao()
    if not config["sincronizacao_nuvem_ativa"]:
        return {"sucesso": False, "erro": "A sincronização com a nuvem está desativada."}
    if config["modo_instalacao"] != "LEITURA":
        return {"sucesso": False, "erro": "A atualização é destinada às instalações de consulta."}
    pasta = _pasta(config)
    versoes = sorted(pasta.glob("clinica_versao_*.db"), reverse=True)
    if not versoes:
        return {"sucesso": False, "erro": "Nenhuma versão publicada foi encontrada."}
    origem = versoes[0]
    _validar_banco(origem)
    seguranca = criar_backup("antes_atualizacao_nuvem")
    fonte = sqlite3.connect(origem)
    destino = banco.conectar()
    try:
        fonte.backup(destino)
    finally:
        destino.close()
        fonte.close()
    _validar_banco(banco.CAMINHO_BANCO)
    return {"sucesso": True, "arquivo": origem.name, "backup_anterior": str(seguranca)}
