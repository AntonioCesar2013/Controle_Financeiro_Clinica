"""Popula todas as tabelas com um cenário inteiramente fictício para testes."""

import json
import sys
from pathlib import Path


# Permite executar pelo botão Run do VS Code ou diretamente com
# ``python src/popular_banco.py``, além do modo de módulo recomendado.
if __package__ in (None, ""):
    raiz_projeto = Path(__file__).resolve().parent.parent
    if str(raiz_projeto) not in sys.path:
        sys.path.insert(0, str(raiz_projeto))

from src.backup_banco import criar_backup
from src.banco import conectar, criar_tabelas
from src.colaboradores import gerar_hash_senha
from src.internacoes import sincronizar_status_residentes


TABELAS_LIMPEZA = (
    "auditoria", "recebimentos", "cobrancas", "vendas_cantina_itens",
    "movimentacoes_carteira", "movimentacoes_estoque", "vendas_cantina",
    "carteiras", "itens_valores", "itens", "pagamentos_saida", "contas_pagar",
    "despesas", "setores", "entradas_bancarias", "internacoes",
    "residente_responsavel", "convenios", "responsaveis", "residentes",
    "colaboradores", "configuracoes_financeiras",
)


def _limpar(conexao):
    for tabela in TABELAS_LIMPEZA:
        conexao.execute(f"DELETE FROM {tabela}")
    for tabela in TABELAS_LIMPEZA:
        conexao.execute("DELETE FROM sqlite_sequence WHERE name=?", (tabela,))


def _popular_pessoas(conexao):
    conexao.executemany(
        "INSERT INTO colaboradores(nome,cpf,senha_hash,status) VALUES(?,?,?,?)",
        [("Administrador Demonstração", "90000000001", gerar_hash_senha("admin1234"), "ATIVO"),
         ("Operador Financeiro", "90000000002", gerar_hash_senha("financeiro123"), "ATIVO"),
         ("Operador Inativo", "90000000003", gerar_hash_senha("inativo123"), "INATIVO")],
    )
    conexao.executemany(
        "INSERT INTO residentes(nome,cpf,cidade_origem,ativo) VALUES(?,?,?,0)",
        [("João Exemplo Particular", "91000000001", "Cascavel"),
         ("Carlos Exemplo Social", "91000000002", "Toledo"),
         ("Pedro Exemplo Convênio", "91000000003", "Foz do Iguaçu"),
         ("Lucas Exemplo Voluntário", "91000000004", "Maringá"),
         ("Marcos Exemplo Futuro", "91000000005", "Londrina")],
    )
    conexao.executemany(
        "INSERT INTO responsaveis(nome,cpf,telefone,email,ativo) VALUES(?,?,?,?,?)",
        [("Maria Responsável Particular", "92000000001", "45999990001", "maria@exemplo.test", 1),
         ("Ana Responsável Social", "92000000002", "45999990002", "ana@exemplo.test", 1),
         ("Paulo Responsável Convênio", "92000000003", "45999990003", "paulo@exemplo.test", 1),
         ("Clara Responsável Voluntário", "92000000004", "45999990004", "clara@exemplo.test", 1),
         ("Rita Responsável Futuro", "92000000005", "45999990005", "rita@exemplo.test", 1),
         ("Responsável Inativo", "92000000006", "45999990006", None, 0)],
    )
    conexao.executemany(
        "INSERT INTO residente_responsavel(residente_id,responsavel_id,relacao,principal) VALUES(?,?,?,1)",
        [(i, i, "Responsável principal fictício") for i in range(1, 6)],
    )


def _popular_internacoes(conexao):
    conexao.executemany(
        "INSERT INTO convenios(nome,valor_diaria,ativo) VALUES(?,?,?)",
        [("Saúde Exemplo", 18500, 1), ("Bem-Estar Demonstração", 22000, 1),
         ("Convênio Inativo", 15000, 0)],
    )
    conexao.executemany(
        """INSERT INTO internacoes(
               residente_id,responsavel_id,data_acolhimento,periodo_tratamento,
               valor_contrato,valor_acolhimento,valor_mensalidade,status,
               modalidade,convenio_id,valor_diaria,servicos_voluntario)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(1, 1, "2026-08-10", 3, 900000, 150000, 250000, "ATIVA", "PARTICULAR", None, 0, None),
         (2, 2, "2026-07-15", 6, 0, 0, 0, "ATIVA", "SOCIAL", None, 0, None),
         (3, 3, "2026-08-20", 3, 1720500, 0, 0, "ATIVA", "CONVENIO", 1, 18500, None),
         (4, 4, "2026-06-01", 0, 0, 0, 0, "ATIVA", "VOLUNTARIO", None, 0,
          "Auxílio na horta e organização da biblioteca."),
         (5, 5, "2026-10-01", 2, 600000, 100000, 250000, "AGENDADA", "PARTICULAR", None, 0, None)],
    )
    conexao.executemany(
        "INSERT INTO cobrancas(internacao_id,numero_parcela,tipo,data_vencimento,valor,desconto,status) VALUES(?,?,?,?,?,?,?)",
        [(1, 0, "ACOLHIMENTO", "2026-08-10", 150000, 0, "PAGA"),
         (1, 1, "MENSALIDADE", "2026-09-10", 250000, 0, "PARCIAL"),
         (1, 2, "MENSALIDADE", "2026-10-10", 250000, 25000, "ABERTA"),
         (1, 3, "MENSALIDADE", "2026-11-10", 250000, 0, "ABERTA"),
         (3, 1, "MENSALIDADE", "2026-08-31", 222000, 0, "PAGA"),
         (3, 2, "MENSALIDADE", "2026-09-30", 555000, 0, "ABERTA"),
         (3, 3, "MENSALIDADE", "2026-10-31", 573500, 0, "ABERTA"),
         (3, 4, "MENSALIDADE", "2026-11-20", 370000, 0, "ABERTA"),
         (5, 0, "ACOLHIMENTO", "2026-10-01", 100000, 0, "ABERTA"),
         (5, 1, "MENSALIDADE", "2026-11-01", 250000, 0, "ABERTA"),
         (5, 2, "MENSALIDADE", "2026-12-01", 250000, 0, "ABERTA")],
    )
    conexao.executemany(
        "INSERT INTO recebimentos(cobranca_id,data_recebimento,valor,forma_recebimento,observacao) VALUES(?,?,?,?,?)",
        [(1, "2026-08-10", 150000, "PIX", "Acolhimento quitado"),
         (2, "2026-09-01", 100000, "PIX", "Pagamento parcial fictício"),
         (5, "2026-08-31", 222000, "TRANSFERENCIA", "Repasse do convênio")],
    )


def _popular_financeiro(conexao):
    conexao.executemany("INSERT INTO setores(nome,ativo) VALUES(?,1)",
                        [("Administração",), ("Cozinha",), ("Cantina",), ("Manutenção",), ("Transporte",)])
    conexao.executemany(
        "INSERT INTO despesas(setor_id,descricao,natureza,recorrente,ativo) VALUES(?,?,?,?,1)",
        [(1, "Energia elétrica fictícia", "FIXA", 1),
         (2, "Compra mensal de alimentos", "VARIAVEL", 1),
         (3, "Reposição de produtos da Cantina", "VARIAVEL", 0),
         (4, "Manutenção preventiva", "FIXA", 1),
         (5, "Combustível dos veículos", "VARIAVEL", 1)],
    )
    conexao.executemany(
        "INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status) VALUES(?,?,?,?)",
        [(1, "2026-09-10", 48000, "PAGA"), (2, "2026-09-05", 135000, "PARCIAL"),
         (3, "2026-09-12", 75000, "ABERTA"), (4, "2026-09-20", 90000, "CANCELADA"),
         (5, "2026-09-08", 60000, "ABERTA")],
    )
    conexao.executemany(
        "INSERT INTO pagamentos_saida(conta_pagar_id,data_pagamento,valor,forma_pagamento,observacao) VALUES(?,?,?,?,?)",
        [(1, "2026-09-10", 48000, "PIX", "Pagamento integral fictício"),
         (2, "2026-09-05", 50000, "PIX", "Primeiro pagamento fictício")],
    )
    conexao.executemany(
        "INSERT INTO entradas_bancarias(data_entrada,descricao,valor,forma_recebimento,origem_documento,observacao) VALUES(?,?,?,?,?,?)",
        [("2026-09-01", "Doação fictícia", 30000, "PIX", "POPULADOR", "Sem vínculo com cobrança"),
         ("2026-09-02", "Contribuição fictícia", 45000, "PIX", "POPULADOR", "Aguardando conciliação")],
    )
    conexao.execute(
        """INSERT INTO configuracoes_financeiras(
               aplicar_juros,tipo_juros,valor_juros,aplicar_multa,tipo_multa,valor_multa,ativo)
           VALUES(1,'PERCENTUAL',100,1,'PERCENTUAL',200,1)"""
    )


def _popular_cantina(conexao):
    conexao.executemany(
        """INSERT INTO itens(nome,codigo_barras,descricao,categoria,unidade_medida,estoque_atual,estoque_minimo,ativo)
           VALUES(?,?,?,?,?,?,?,?)""",
        [("Água mineral fictícia", "7891000000001", "Garrafa 500 ml", "Bebidas", "UN", 22, 5, 1),
         ("Chocolate fictício", "7891000000002", "Barra 80 g", "Doces", "UN", 14, 4, 1),
         ("Kit de higiene fictício", "7891000000003", "Sabonete e creme dental", "Higiene", "KIT", 8, 3, 1),
         ("Corte de cabelo fictício", "7891000000004", "Serviço terceirizado", "Serviços", "UN", 0, 0, 1),
         ("Produto inativo fictício", "7891000000005", "Somente para testar filtros", "Outros", "UN", 0, 0, 0)],
    )
    conexao.executemany(
        "INSERT INTO itens_valores(item_id,valor,data_inicio_valor,ativo) VALUES(?,?,?,?)",
        [(1, 4.00, "2026-08-01", 1), (2, 7.50, "2026-08-01", 1),
         (3, 18.00, "2026-08-01", 1), (4, 25.00, "2026-08-01", 1),
         (5, 3.00, "2026-08-01", 1), (2, 6.50, "2026-07-01", 0)],
    )
    conexao.executemany("INSERT INTO carteiras(residente_id,saldo,ativo) VALUES(?,?,1)",
                        [(1, 72.50), (2, -25.00), (3, 150.00), (4, 0.00)])
    conexao.executemany(
        "INSERT INTO vendas_cantina(carteira_id,data_movimentacao,valor_total,status) VALUES(?,?,?,'FINALIZADA')",
        [(1, "2026-09-01", 11.50), (2, "2026-09-01", 25.00)],
    )
    conexao.executemany(
        "INSERT INTO vendas_cantina_itens(venda_id,item_id,item_valor_id,quantidade,valor_unitario,valor_total) VALUES(?,?,?,?,?,?)",
        [(1, 1, 1, 1, 4.00, 4.00), (1, 2, 2, 1, 7.50, 7.50), (2, 4, 4, 1, 25.00, 25.00)],
    )
    conexao.executemany(
        """INSERT INTO movimentacoes_carteira(
               carteira_id,tipo,item_id,quantidade,item_valor_id,valor_total,data_movimentacao,venda_id)
           VALUES(?,?,?,?,?,?,?,?)""",
        [(1, "CREDITO", None, 1, None, 84.00, "2026-08-30", None),
         (1, "COMPRA", 1, 1, 1, -4.00, "2026-09-01", 1),
         (1, "COMPRA", 2, 1, 2, -7.50, "2026-09-01", 1),
         (2, "COMPRA", 4, 1, 4, -25.00, "2026-09-01", 2),
         (3, "CREDITO", None, 1, None, 150.00, "2026-08-31", None)],
    )
    conexao.executemany(
        """INSERT INTO movimentacoes_estoque(
               item_id,quantidade_anterior,quantidade_movimentada,quantidade_atual,motivo,
               data_movimentacao,tipo,venda_id,custo_unitario,fornecedor,documento,lote,data_validade)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(1, 0, 25, 25, "Estoque inicial fictício", "2026-08-01", "ENTRADA", None, 2.00, "Fornecedor Exemplo", "NF-001", "A01", "2027-01-31"),
         (1, 25, -1, 24, "Venda Cantina #1", "2026-09-01", "VENDA", 1, None, None, None, None, None),
         (1, 24, -2, 22, "Ajuste por avaria", "2026-09-01", "SAIDA", None, None, None, None, None, None),
         (2, 0, 15, 15, "Estoque inicial fictício", "2026-08-01", "ENTRADA", None, 4.00, "Fornecedor Exemplo", "NF-002", "C01", "2027-03-31"),
         (2, 15, -1, 14, "Venda Cantina #1", "2026-09-01", "VENDA", 1, None, None, None, None, None),
         (3, 0, 8, 8, "Estoque inicial fictício", "2026-08-01", "ENTRADA", None, 10.00, "Fornecedor Exemplo", "NF-003", "H01", "2028-01-31")],
    )


def _popular_auditoria(conexao):
    eventos = [
        (1, "Administrador Demonstração", "INCLUSAO", "residentes", "1", {"nome": "João Exemplo Particular"}),
        (2, "Operador Financeiro", "INCLUSAO", "recebimentos", "1", {"forma_pagamento": "PIX", "valor": 1500.00}),
        (1, "Administrador Demonstração", "ALTERACAO", "internacoes", "3", {"modalidade": "CONVENIO"}),
    ]
    conexao.executemany(
        "INSERT INTO auditoria(colaborador_id,colaborador_nome,acao,entidade,entidade_id,detalhes,endereco_ip) VALUES(?,?,?,?,?,?,?)",
        [(colaborador, nome, acao, entidade, entidade_id, json.dumps(detalhes, ensure_ascii=False), "127.0.0.1")
         for colaborador, nome, acao, entidade, entidade_id, detalhes in eventos],
    )


def _resumo(conexao):
    print("\n=== RESUMO DO BANCO FICTÍCIO ===")
    for tabela in reversed(TABELAS_LIMPEZA):
        print(f"{tabela}: {conexao.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0]}")
    print("\nAcesso fictício: CPF 90000000001 | senha admin1234")


def popular_banco(fazer_backup=True):
    criar_tabelas()
    backup = criar_backup("antes_populador_ficticio") if fazer_backup else None
    conexao = conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        _limpar(conexao)
        _popular_pessoas(conexao)
        _popular_internacoes(conexao)
        _popular_financeiro(conexao)
        _popular_cantina(conexao)
        _popular_auditoria(conexao)
        conexao.commit()
        _resumo(conexao)
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()
    sincronizar_status_residentes("2026-09-01")
    if backup:
        print(f"\nBackup anterior preservado em: {backup}")
    print("\n=== BANCO POPULADO COM SUCESSO ===")


if __name__ == "__main__":
    popular_banco()
