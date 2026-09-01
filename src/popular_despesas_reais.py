"""Substitui os dados de demonstração pelas despesas reais de agosto de 2026."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from src.banco import CAMINHO_BANCO, criar_tabelas


COMPRAS_REAIS = (
    {
        "setor": "Compras gerais", "tipo": "Supermercado e abastecimento",
        "descricao": "Mercado Lorena - compra geral", "data": "2026-08-27",
        "valor": 34566, "forma": "PIX",
        "observacao": "Fonte: relatorio_compras_clinica_da_cruz_pronto_impressao.pdf.",
    },
    {
        "setor": "Cozinha", "tipo": "Gêneros alimentícios",
        "descricao": "Carne suína - 60 kg", "data": "2026-08-26",
        "valor": 58125, "forma": "PIX",
        "observacao": "Fornecedor não informado. Fonte: relatorio_compras_clinica_da_cruz_pronto_impressao.pdf.",
    },
    {
        "setor": "Compras gerais", "tipo": "Supermercado e abastecimento",
        "descricao": "Supermercados do Brasil Ltda. - compra institucional",
        "data": "2026-08-17", "valor": 574423, "forma": "CARTÃO DE CRÉDITO",
        "observacao": "Valor líquido após R$ 113,54 de descontos. Fonte: Relatorio_Institucional_Compras_17-08-2026_Clinica_da_Cruz.pdf.",
    },
    {
        "setor": "Cozinha", "tipo": "Gêneros alimentícios",
        "descricao": "Copacol - itens 01 a 10 do comprovante", "data": "2026-08-28",
        "valor": 68180, "forma": "PIX",
        "observacao": "Data da compra ausente no documento; usada a data de registro/importação (28/08/2026). O relatório abrange somente os itens 01 a 10. Fonte: Relatorio_Compra_Itens_01_a_10_Clinica_da_Cruz.pdf.",
    },
    {
        "setor": "Cozinha", "tipo": "Gêneros alimentícios",
        "descricao": "Paraná Supermercados - carnes e margarina", "data": "2026-08-20",
        "valor": 58722, "forma": "CARTÃO / CONVÊNIO",
        "observacao": "Controle 069608. Fonte: Relatorio_de_Compras_Parana_Clinica_da_Cruz_sem_anexo.pdf.",
    },
    {
        "setor": "Cozinha", "tipo": "Gêneros alimentícios",
        "descricao": "Supermercado Paraná - compra de alimentos", "data": "2026-08-25",
        "valor": 107552, "forma": "CARTÃO / CONVÊNIO",
        "observacao": "Valor líquido após R$ 75,71 de descontos; controle 069733. Fonte: Relatorio_de_Compras_Supermercado_Parana_25-08-2026.pdf.",
    },
    {
        "setor": "Cantina", "tipo": "Estoque da cantina",
        "descricao": "Doces Grizotto Oliveira Ltda. - estoque da cantina",
        "data": "2026-08-26", "valor": 53740, "forma": "PIX",
        "observacao": "Data da compra não visível; usada a data de emissão do relatório (26/08/2026). Valor após ajuste de R$ 23,96. Fonte: Relatorio_Financeiro_Cantina_Clinica_da_Cruz.pdf.",
    },
    {
        "setor": "Cozinha", "tipo": "Gêneros alimentícios",
        "descricao": "Mercado Lorena - 11 unidades de óleo de soja",
        "data": "2026-08-26", "valor": 8019, "forma": "CARTÃO",
        "observacao": "Documento/orçamento F02-000169935. Fonte: Relatorio_Compras_Cozinha_Clinica_da_Cruz_26-08-2026.pdf.",
    },
)


TABELAS_DEMONSTRACAO = (
    "recebimentos", "entradas_bancarias", "cobrancas", "vendas_cantina_itens",
    "movimentacoes_carteira", "vendas_cantina", "carteiras",
    "internacoes", "residente_responsavel", "responsaveis", "residentes",
    "pagamentos_saida", "contas_pagar", "despesas",
    "setores", "itens_valores", "itens",
)


def _backup(caminho: Path, rotulo: str = "despesas_reais") -> Path:
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = caminho.with_name(f"{caminho.stem}_antes_{rotulo}_{carimbo}{caminho.suffix}")
    shutil.copy2(caminho, destino)
    return destino


def popular(caminho_banco: Path = CAMINHO_BANCO, fazer_backup: bool = True):
    caminho_banco = Path(caminho_banco)
    if caminho_banco == CAMINHO_BANCO:
        criar_tabelas()
    if not caminho_banco.exists():
        raise FileNotFoundError(f"Banco não encontrado: {caminho_banco}")

    backup = _backup(caminho_banco) if fazer_backup else None
    conn = sqlite3.connect(caminho_banco)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN")
        tabelas_existentes = {
            linha[0] for linha in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for tabela in TABELAS_DEMONSTRACAO:
            if tabela in tabelas_existentes:
                conn.execute(f"DELETE FROM {tabela}")
        conn.executemany(
            "DELETE FROM sqlite_sequence WHERE name = ?",
            ((tabela,) for tabela in TABELAS_DEMONSTRACAO),
        )

        setores = {}
        for compra in COMPRAS_REAIS:
            if compra["setor"] not in setores:
                cursor = conn.execute("INSERT INTO setores (nome) VALUES (?)", (compra["setor"],))
                setores[compra["setor"]] = cursor.lastrowid
            cursor = conn.execute(
                "INSERT INTO despesas (setor_id, descricao, natureza, recorrente) VALUES (?, ?, 'VARIAVEL', 0)",
                (setores[compra["setor"]], compra["descricao"]),
            )
            despesa_id = cursor.lastrowid
            cursor = conn.execute(
                "INSERT INTO contas_pagar (despesa_id, data_vencimento, valor, status) VALUES (?, ?, ?, 'PAGA')",
                (despesa_id, compra["data"], compra["valor"]),
            )
            conn.execute(
                "INSERT INTO pagamentos_saida (conta_pagar_id, data_pagamento, valor, forma_pagamento, observacao) VALUES (?, ?, ?, ?, ?)",
                (cursor.lastrowid, compra["data"], compra["valor"], compra["forma"], compra["observacao"]),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {"backup": backup, "quantidade": len(COMPRAS_REAIS), "total": sum(c["valor"] for c in COMPRAS_REAIS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-backup", action="store_true")
    args = parser.parse_args()
    resultado = popular(fazer_backup=not args.sem_backup)
    print(f"{resultado['quantidade']} despesas reais registradas; total R$ {resultado['total'] / 100:,.2f}.")
    if resultado["backup"]:
        print(f"Backup: {resultado['backup']}")


if __name__ == "__main__":
    main()
