import argparse
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from src.infraestrutura import banco


PASTA_BACKUPS = banco.CAMINHO_BANCO.parent / "backups"


def _validar_banco(caminho):
    try:
        conexao = sqlite3.connect(Path(caminho).resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as erro:
        raise ValueError("O arquivo não é um banco SQLite válido.") from erro
    try:
        integridade = conexao.execute("PRAGMA integrity_check").fetchall()
        tabelas = {linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        base = {"residentes", "internacoes", "colaboradores", "carteiras", "cobrancas"}
        cantina = ({"itens_cantina", "itens_cantina_valores"}.issubset(tabelas)
                   or {"itens", "itens_valores"}.issubset(tabelas))
        if integridade != [("ok",)] or not base.issubset(tabelas) or not cantina:
            raise ValueError("O arquivo não é um backup íntegro deste sistema.")
    except sqlite3.Error as erro:
        raise ValueError("O arquivo não é um backup íntegro deste sistema.") from erro
    finally:
        conexao.close()


def criar_backup(rotulo="automatico"):
    banco.criar_tabelas()
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    seguro = "".join(c for c in str(rotulo) if c.isalnum() or c in "-_") or "backup"
    destino = PASTA_BACKUPS / f"clinica_{datetime.now():%Y%m%d_%H%M%S_%f}_{seguro}.db"
    from src.infraestrutura.backup.snapshot import create_snapshot
    create_snapshot(banco.CAMINHO_BANCO, destino)
    _validar_banco(destino)
    return destino


def listar_backups(config=None):
    pastas = [PASTA_BACKUPS]
    try:
        from src.infraestrutura.backup.config import BackupConfig
        configurada = (config or BackupConfig()).load().get("backup_directory")
        if configurada:
            pastas.append(Path(configurada))
    except (OSError, ValueError, ImportError):
        pass
    encontrados = {}
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for padrao in ("clinica_*.db", "controle_financeiro_*.db"):
            for arquivo in pasta.glob(padrao):
                encontrados[str(arquivo.resolve()).casefold()] = arquivo.resolve()
    return sorted(encontrados.values(), key=lambda item: item.stat().st_mtime, reverse=True)


def criar_backup_diario(retencao=30):
    hoje = datetime.now().strftime("%Y%m%d")
    existentes = listar_backups()
    diario = next((item for item in existentes if item.name.startswith(f"clinica_{hoje}_") and item.name.endswith("_diario.db")), None)
    criado = diario or criar_backup("diario")
    # Compatibilidade: nenhuma exclusão automática sem política configurada.
    return criado


def restaurar_backup(nome_arquivo, config=None):
    informado = Path(str(nome_arquivo))
    catalogo = listar_backups(config)
    if informado.is_absolute():
        candidatos = [item for item in catalogo if item == informado.resolve()]
    else:
        candidatos = [item for item in catalogo if item.name == informado.name]
    if not candidatos:
        raise ValueError("Backup não encontrado nas pastas de backup reconhecidas pelo sistema.")
    if len(candidatos) > 1:
        raise ValueError("Há mais de um backup com esse nome. Informe o caminho completo exibido na listagem.")
    origem = candidatos[0]
    _validar_banco(origem)

    from src.infraestrutura.backup.snapshot import create_snapshot
    from src.infraestrutura.uso_banco import TravaUsoBanco
    with TravaUsoBanco(banco.CAMINHO_BANCO):
        PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
        seguranca = PASTA_BACKUPS / f"clinica_{datetime.now():%Y%m%d_%H%M%S_%f}_antes_restauracao.db"
        create_snapshot(banco.CAMINHO_BANCO, seguranca)
        _validar_banco(seguranca)
        fd, temporario = tempfile.mkstemp(prefix="restauracao_", suffix=".db", dir=banco.CAMINHO_BANCO.parent)
        os.close(fd)
        Path(temporario).unlink(missing_ok=True)
        try:
            create_snapshot(origem, temporario)
            _validar_banco(temporario)
            os.replace(temporario, banco.CAMINHO_BANCO)
        finally:
            Path(temporario).unlink(missing_ok=True)
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
            print(arquivo)
    else:
        resultado = restaurar_backup(args.arquivo)
        print(f"Banco restaurado de: {resultado['restaurado']}")
        print(f"Cópia anterior preservada em: {resultado['backup_anterior']}")


if __name__ == "__main__":
    main()
