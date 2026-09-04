"""Populador determinístico com seis meses de operação fictícia da clínica."""

import json
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    raiz = Path(__file__).resolve().parents[2]
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))

from src.cadastros.colaboradores import gerar_hash_senha
from src.cadastros.internacoes import sincronizar_status_residentes
from src.infraestrutura.backup_banco import criar_backup
from src.infraestrutura.banco import conectar, criar_tabelas


MESES = tuple((2026, mes) for mes in range(3, 9))
TABELAS_LIMPEZA = (
    "recibos", "estornos_financeiros", "ajustes_cobrancas", "auditoria",
    "recebimentos", "cobrancas", "vendas_cantina_itens", "movimentacoes_carteira",
    "movimentacoes_estoque", "vendas_cantina", "carteiras", "itens_valores",
    "itens", "pagamentos_saida", "contas_pagar", "despesas", "setores",
    "entradas_bancarias", "internacoes", "residente_responsavel", "convenios",
    "responsaveis", "residentes", "colaboradores", "configuracoes_financeiras",
)


def _data(ano, mes, dia):
    return date(ano, mes, min(dia, monthrange(ano, mes)[1])).isoformat()


def _limpar(conn):
    for tabela in TABELAS_LIMPEZA:
        conn.execute(f"DELETE FROM {tabela}")
    for tabela in TABELAS_LIMPEZA:
        conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (tabela,))


def _pessoas(conn):
    conn.executemany(
        "INSERT INTO colaboradores(nome,cpf,senha_hash,status) VALUES(?,?,?,?)",
        [("Administrador Demonstração", "90000000001", gerar_hash_senha("admin1234"), "ATIVO"),
         ("Operador Financeiro", "90000000002", gerar_hash_senha("financeiro123"), "ATIVO"),
         ("Operador Inativo", "90000000003", gerar_hash_senha("inativo123"), "INATIVO")],
    )
    nomes = ("Alice", "Bruno", "Caio", "Daniel", "Eduardo", "Felipe", "Gustavo",
             "Henrique", "Igor", "João", "Leandro", "Marcos", "Nicolas Social", "Otávio Voluntário")
    cidades = ("Cascavel", "Toledo", "Foz do Iguaçu", "Maringá", "Londrina", "Curitiba")
    conn.executemany(
        "INSERT INTO residentes(nome,cpf,cidade_origem,ativo) VALUES(?,?,?,1)",
        [(f"{nome} Exemplo", f"910000000{i:02d}", cidades[(i - 1) % 6]) for i, nome in enumerate(nomes, 1)],
    )
    conn.executemany(
        "INSERT INTO responsaveis(nome,cpf,telefone,email,ativo) VALUES(?,?,?,?,1)",
        [(f"Responsável {nome}", f"920000000{i:02d}", f"4599900{i:04d}", f"responsavel{i}@exemplo.test")
         for i, nome in enumerate(nomes, 1)],
    )
    conn.executemany(
        "INSERT INTO residente_responsavel(residente_id,responsavel_id,relacao,principal) VALUES(?,?,?,1)",
        [(i, i, "Responsável principal fictício") for i in range(1, 15)],
    )


def _internacoes(conn):
    conn.executemany(
        "INSERT INTO convenios(nome,valor_diaria,ativo) VALUES(?,?,?)",
        [("Saúde Exemplo", 18500, 1), ("Bem-Estar Demonstração", 22000, 1)],
    )
    valores = [220000, 235000, 245000, 250000, 260000, 275000,
               285000, 300000, 315000, 325000, 340000, 360000]
    registros = []
    for residente, mensalidade in enumerate(valores, 1):
        convenio = residente in (11, 12)
        registros.append((residente, residente, "2026-02-10", 12, mensalidade * 7 + 120000,
                          120000, mensalidade, "ATIVA", "CONVENIO" if convenio else "PARTICULAR",
                          1 if convenio else None, 18500 if convenio else 0, None))
    registros += [
        (13, 13, "2026-02-15", 12, 0, 0, 0, "ATIVA", "SOCIAL", None, 0, None),
        (14, 14, "2026-02-01", 0, 0, 0, 0, "ATIVA", "VOLUNTARIO", None, 0, "Horta e biblioteca"),
    ]
    conn.executemany(
        """INSERT INTO internacoes(residente_id,responsavel_id,data_acolhimento,periodo_tratamento,
           valor_contrato,valor_acolhimento,valor_mensalidade,status,modalidade,convenio_id,
           valor_diaria,servicos_voluntario) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", registros,
    )
    cobrancas, recebimentos = [], []
    cobranca_id = 0
    for residente, mensalidade in enumerate(valores, 1):
        cobranca_id += 1
        cobrancas.append((residente, 0, "ACOLHIMENTO", "2026-02-10", 120000, 0, "PAGA"))
        recebimentos.append((cobranca_id, "2026-02-10", 120000, "PIX", "Acolhimento fictício"))
        for parcela, (ano, mes) in enumerate((*MESES, (2026, 9)), 1):
            cobranca_id += 1
            desconto = 15000 if (residente, mes) in {(2, 6), (9, 4)} else 0
            inadimplente = (residente, mes) in {(4, 7), (4, 8), (8, 8), (11, 6)}
            parcial = (residente, mes) in {(3, 8), (7, 5)}
            status = "ABERTA" if mes == 9 or inadimplente else "PARCIAL" if parcial else "PAGA"
            cobrancas.append((residente, parcela, "MENSALIDADE", _data(ano, mes, 10 + residente % 8),
                               mensalidade, desconto, status))
            if status in ("PAGA", "PARCIAL"):
                pago = (mensalidade - desconto) // 2 if parcial else mensalidade - desconto
                forma = ("PIX", "DINHEIRO", "CARTAO", "TRANSFERENCIA", "BOLETO")[(residente + mes) % 5]
                recebimentos.append((cobranca_id, _data(ano, mes, 8 + residente % 10), pago, forma,
                                      "Pagamento parcial fictício" if parcial else "Mensalidade fictícia quitada"))
    conn.executemany(
        "INSERT INTO cobrancas(internacao_id,numero_parcela,tipo,data_vencimento,valor,desconto,status) VALUES(?,?,?,?,?,?,?)",
        cobrancas,
    )
    conn.executemany(
        "INSERT INTO recebimentos(cobranca_id,data_recebimento,valor,forma_recebimento,observacao) VALUES(?,?,?,?,?)",
        recebimentos,
    )


def _financeiro(conn):
    setores = ("Administração", "Cozinha", "Saúde", "Manutenção", "Transporte", "Cantina")
    conn.executemany("INSERT INTO setores(nome,ativo) VALUES(?,1)", [(x,) for x in setores])
    descricoes = ("Energia elétrica", "Água e saneamento", "Internet e telefonia", "Alimentos",
                  "Produtos de limpeza", "Medicamentos", "Materiais de enfermagem", "Manutenção predial",
                  "Jardinagem", "Combustível", "Seguro dos veículos", "Contabilidade", "Material de escritório",
                  "Gás de cozinha", "Lavanderia", "Coleta de resíduos", "Reposição da cantina", "Terapias externas")
    conn.executemany(
        "INSERT INTO despesas(setor_id,descricao,natureza,recorrente,ativo) VALUES(?,?,?,?,1)",
        [(i % 6 + 1, descricao, "FIXA" if i % 3 == 0 else "VARIAVEL", int(i < 16))
         for i, descricao in enumerate(descricoes)],
    )
    conta_id = 0
    for indice, (ano, mes) in enumerate(MESES):
        for despesa in range(1, 19):
            conta_id += 1
            valor = 28000 + despesa * 7300 + indice * 1900
            desconto = 5000 if (despesa, mes) in {(6, 4), (12, 7)} else 0
            aberta, parcial = despesa in (16, 18), despesa == 15 and mes in (5, 8)
            status = "ABERTA" if aberta else "PARCIAL" if parcial else "PAGA"
            conn.execute(
                "INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,desconto,status) VALUES(?,?,?,?,?)",
                (despesa, _data(ano, mes, 4 + despesa), valor, desconto, status),
            )
            if not aberta:
                pago = (valor - desconto) // 2 if parcial else valor - desconto
                forma = ("PIX", "DINHEIRO", "CARTAO", "TRANSFERENCIA", "BOLETO")[(despesa + mes) % 5]
                conn.execute(
                    "INSERT INTO pagamentos_saida(conta_pagar_id,data_pagamento,valor,forma_pagamento,observacao) VALUES(?,?,?,?,?)",
                    (conta_id, _data(ano, mes, 6 + despesa), pago, forma,
                     "Pagamento parcial fictício" if parcial else "Pagamento integral fictício"),
                )
        for entrada in range(1, 7):
            conn.execute(
                """INSERT INTO entradas_bancarias(data_entrada,descricao,valor,forma_recebimento,
                   origem_documento,observacao) VALUES(?,?,?,?,?,?)""",
                (_data(ano, mes, 2 + entrada * 4), f"Doação institucional {entrada}",
                 20000 + entrada * 7500 + indice * 1000, "PIX" if entrada % 2 else "TRANSFERENCIA",
                 f"DOACAO-{ano}{mes:02d}-{entrada:02d}", "Entrada fictícia sem vínculo com cobrança"),
            )
    conn.execute(
        """INSERT INTO configuracoes_financeiras(aplicar_juros,tipo_juros,valor_juros,
           aplicar_multa,tipo_multa,valor_multa,ativo) VALUES(1,'PERCENTUAL',100,1,'PERCENTUAL',200,1)"""
    )


def _cantina(conn):
    itens = (("Água mineral", "7891000000001", "Bebidas", 400, 1200),
             ("Suco", "7891000000002", "Bebidas", 650, 900),
             ("Biscoito", "7891000000003", "Alimentos", 750, 850),
             ("Chocolate", "7891000000004", "Doces", 900, 700),
             ("Kit de higiene", "7891000000005", "Higiene", 2200, 400),
             ("Corte de cabelo", "7891000000006", "Serviços", 3000, 0))
    conn.executemany(
        """INSERT INTO itens(nome,codigo_barras,descricao,categoria,unidade_medida,
           estoque_atual,estoque_minimo,ativo) VALUES(?,?,?,?,'UN',?,?,1)""",
        [(n, c, f"{n} fictício", cat, estoque, 20 if estoque else 0) for n, c, cat, _, estoque in itens],
    )
    conn.executemany("INSERT INTO itens_valores(item_id,valor,data_inicio_valor,ativo) VALUES(?,?,?,1)",
                     [(i, item[3], "2026-03-01") for i, item in enumerate(itens, 1)])
    conn.executemany("INSERT INTO carteiras(residente_id,saldo,ativo) VALUES(?,0,1)", [(i,) for i in range(1, 13)])
    estoques = {i: item[4] for i, item in enumerate(itens, 1)}
    saldos = {i: 0 for i in range(1, 13)}
    venda = 0
    for item, quantidade in estoques.items():
        if quantidade:
            conn.execute("""INSERT INTO movimentacoes_estoque(item_id,quantidade_anterior,quantidade_movimentada,
                         quantidade_atual,motivo,data_movimentacao,tipo) VALUES(?,0,?,?,?,'2026-03-01','ENTRADA')""",
                         (item, quantidade, quantidade, "Estoque inicial fictício"))
    for ano, mes in MESES:
        for carteira in range(1, 13):
            credito = 12000 + carteira * 500
            saldos[carteira] += credito
            conn.execute("INSERT INTO movimentacoes_carteira(carteira_id,tipo,quantidade,valor_total,data_movimentacao) VALUES(?,'CREDITO',1,?,?)",
                         (carteira, credito, _data(ano, mes, 2)))
            venda += 1
            item = (carteira + mes) % 6 + 1
            quantidade, unitario = 1 + carteira % 2, itens[item - 1][3]
            total = quantidade * unitario
            conn.execute("INSERT INTO vendas_cantina(carteira_id,data_movimentacao,valor_total,status) VALUES(?,?,?,'FINALIZADA')",
                         (carteira, _data(ano, mes, 5 + carteira), total))
            conn.execute("INSERT INTO vendas_cantina_itens(venda_id,item_id,item_valor_id,quantidade,valor_unitario,valor_total) VALUES(?,?,?,?,?,?)",
                         (venda, item, item, quantidade, unitario, total))
            conn.execute("""INSERT INTO movimentacoes_carteira(carteira_id,tipo,item_id,quantidade,item_valor_id,
                         valor_total,data_movimentacao,venda_id) VALUES(?,'COMPRA_CANTINA',?,?,?,?,?,?)""",
                         (carteira, item, quantidade, item, total, _data(ano, mes, 5 + carteira), venda))
            saldos[carteira] -= total
            if estoques[item]:
                anterior = estoques[item]
                estoques[item] -= quantidade
                conn.execute("""INSERT INTO movimentacoes_estoque(item_id,quantidade_anterior,quantidade_movimentada,
                             quantidade_atual,motivo,data_movimentacao,tipo,venda_id) VALUES(?,?,?,?,?,?,'VENDA',?)""",
                             (item, anterior, -quantidade, estoques[item], f"Venda Cantina #{venda}", _data(ano, mes, 5 + carteira), venda))
    conn.executemany("UPDATE carteiras SET saldo=? WHERE id=?", [(v, k) for k, v in saldos.items()])
    conn.executemany("UPDATE itens SET estoque_atual=? WHERE id=?", [(v, k) for k, v in estoques.items()])


def _auditoria(conn):
    eventos = [(1, "Administrador Demonstração", "CONSULTA", "relatorios", f"{a}-{m:02d}",
                json.dumps({"cenario": "ficticio", "mes": m}), "127.0.0.1") for a, m in MESES]
    conn.executemany("INSERT INTO auditoria(colaborador_id,colaborador_nome,acao,entidade,entidade_id,detalhes,endereco_ip) VALUES(?,?,?,?,?,?,?)", eventos)


def _validar(conn):
    linhas = []
    for ano, mes in MESES:
        prefixo = f"{ano}-{mes:02d}"
        recebimentos = conn.execute("SELECT COUNT(*) FROM recebimentos WHERE data_recebimento LIKE ?", (prefixo + "%",)).fetchone()[0]
        entradas = conn.execute("SELECT COUNT(*) FROM entradas_bancarias WHERE data_entrada LIKE ?", (prefixo + "%",)).fetchone()[0]
        pagamentos = conn.execute("SELECT COUNT(*) FROM pagamentos_saida WHERE data_pagamento LIKE ?", (prefixo + "%",)).fetchone()[0]
        cantina = conn.execute("SELECT COUNT(*) FROM vendas_cantina WHERE data_movimentacao LIKE ?", (prefixo + "%",)).fetchone()[0]
        caixa = recebimentos + entradas + pagamentos
        if caixa < 30:
            raise RuntimeError(f"{prefixo} possui somente {caixa} movimentações de caixa")
        linhas.append((prefixo, caixa, recebimentos, entradas, pagamentos, cantina))
    inadimplencias = conn.execute("SELECT COUNT(*) FROM cobrancas WHERE status IN ('ABERTA','PARCIAL') AND data_vencimento<'2026-09-01'").fetchone()[0]
    if inadimplencias < 5:
        raise RuntimeError("O cenário não possui inadimplências suficientes")
    return linhas, inadimplencias


def popular_banco(fazer_backup=True):
    criar_tabelas()
    backup = criar_backup("antes_populador_ficticio_6_meses") if fazer_backup else None
    conn = conectar()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _limpar(conn)
        _pessoas(conn)
        _internacoes(conn)
        _financeiro(conn)
        _cantina(conn)
        _auditoria(conn)
        linhas, inadimplencias = _validar(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    sincronizar_status_residentes("2026-09-04")
    print("\n=== CENÁRIO FICTÍCIO DE SEIS MESES ===")
    for mes, caixa, recebimentos, entradas, pagamentos, cantina in linhas:
        print(f"{mes}: caixa={caixa} (recebimentos={recebimentos}, outras entradas={entradas}, pagamentos={pagamentos}); cantina={cantina}")
    print(f"Inadimplências anteriores a setembro: {inadimplencias}")
    print("Acesso: CPF 90000000001 | senha admin1234")
    if backup:
        print(f"Backup anterior: {backup}")
    print("=== BANCO POPULADO COM SUCESSO ===")


if __name__ == "__main__":
    popular_banco()
