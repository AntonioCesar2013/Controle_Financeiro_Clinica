import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from src import banco


PASTA_BACKUPS = banco.CAMINHO_BANCO.parent / "backups"


def _validar_banco(caminho):
    conexao = sqlite3.connect(caminho)
    try:
        integridade = conexao.execute("PRAGMA integrity_check").fetchone()[0]
        tabelas = {linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if integridade != "ok" or not {"residentes", "internacoes", "colaboradores"}.issubset(tabelas):
            raise ValueError("O arquivo não é um backup íntegro deste sistema.")
    finally:
        conexao.close()


def criar_backup(rotulo="automatico"):
    banco.criar_tabelas()
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    seguro = "".join(c for c in str(rotulo) if c.isalnum() or c in "-_") or "backup"
    destino = PASTA_BACKUPS / f"clinica_{datetime.now():%Y%m%d_%H%M%S_%f}_{seguro}.db"
    origem = banco.conectar()
    copia = sqlite3.connect(destino)
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()
    _validar_banco(destino)
    return destino


def listar_backups():
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    return sorted(PASTA_BACKUPS.glob("clinica_*.db"), key=lambda item: item.stat().st_mtime, reverse=True)


def criar_backup_diario(retencao=30):
    hoje = datetime.now().strftime("%Y%m%d")
    existentes = listar_backups()
    diario = next((item for item in existentes if item.name.startswith(f"clinica_{hoje}_") and item.name.endswith("_diario.db")), None)
    criado = diario or criar_backup("diario")
    diarios = [item for item in listar_backups() if item.name.endswith("_diario.db")]
    for antigo in diarios[int(retencao):]:
        antigo.unlink()
    return criado


def restaurar_backup(nome_arquivo):
    nome = Path(str(nome_arquivo)).name
    origem = (PASTA_BACKUPS / nome).resolve()
    if origem.parent != PASTA_BACKUPS.resolve() or not origem.is_file():
        raise ValueError("Backup não encontrado na pasta de backups do sistema.")
    _validar_banco(origem)
    seguranca = criar_backup("antes_restauracao")
    fonte = sqlite3.connect(origem)
    destino = banco.conectar()
    try:
        fonte.backup(destino)
    finally:
        destino.close()
        fonte.close()
    _validar_banco(banco.CAMINHO_BANCO)
    return {"restaurado": origem, "backup_anterior": seguranca}


def main():
    parser = argparse.ArgumentParser(description="Backup e restauração do banco da clínica")
    sub = parser.add_subparsers(dest="comando", required=True)
    criar = sub.add_parser("criar")
    criar.add_argument("--rotulo", default="manual")
    sub.add_parser("listar")
    restaurar = sub.add_parser("restaurar")
    restaurar.add_argument("arquivo", help="Nome exibido pelo comando listar")
    args = parser.parse_args()
    if args.comando == "criar":
        print(f"Backup criado: {criar_backup(args.rotulo)}")
    elif args.comando == "listar":
        for arquivo in listar_backups():
            print(arquivo.name)
    else:
        resultado = restaurar_backup(args.arquivo)
        print(f"Banco restaurado de: {resultado['restaurado']}")
        print(f"Cópia anterior preservada em: {resultado['backup_anterior']}")


if __name__ == "__main__":
    main()
