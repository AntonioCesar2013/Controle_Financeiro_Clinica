import sqlite3

from src.banco import CAMINHO_BANCO, conectar, criar_tabelas
from src.cobrancas import gerar_cobrancas, listar_cobrancas
from src.contas_pagar import cadastrar_conta, cancelar_conta
from src.despesas import cadastrar_despesa, cadastrar_setor, cadastrar_tipo_despesa
from src.internacoes import cadastrar_internacao
from src.pagamentos import registrar_pagamento as registrar_pagamento_saida
from src.recebimentos import registrar_pagamento as registrar_recebimento
from src.residentes import cadastrar_residente
from src.responsaveis import cadastrar_responsavel


CENTAVOS = 100


def limpar_banco():
    """Remove os dados de teste, preservando a estrutura do banco."""
    tabelas = [
        "recebimentos", "cobrancas", "internacoes", "residente_responsavel",
        "responsaveis", "residentes", "pagamentos_saida", "contas_pagar",
        "despesas", "tipos_despesa", "setores",
    ]
    conn = sqlite3.connect(CAMINHO_BANCO)
    try:
        for tabela in tabelas:
            conn.execute(f"DELETE FROM {tabela}")
        for tabela in tabelas:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabela,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def _exigir_sucesso(resultado, operacao):
    if "sucesso" in resultado and not resultado["sucesso"]:
        raise RuntimeError(f"{operacao}: {resultado.get('erro', 'falhou.')}")
    return resultado


DADOS_INTERNACOES = [
    ("ADEVANIR MENEGHETE JUNIOR", "MARIA ANTONIETA MENEGHETE", "2026-08-08", 3, 10000, 2500, 0),
    ("ANDRE HENRIQUE ALTMANN", "ENEOZI LEMOS DA SILVA ALTMANN", "2026-07-05", 3, 8800, 2200, 0),
    ("ANGEL MOISÉS PERALTA GONZALEZ", "LIZ TATIANA RIBEIROS", "2026-04-18", 6, 17500, 2500, 0),
    ("CELSO DE LIMA", "IDINIR DE LIMA", "2026-07-11", 6, 0, 0, 0),
    ("CÍCERO DE OLIVEIRA", "SONILDA PERALTA FERNANDES", "2026-07-21", 3, 10000, 2500, 0),
    ("CLEOSMAR GOBETTI RIBEIRO GOMES", "FUNDO M. SAUDE DE BOA VISTA", "2026-03-10", 10, 45235.92, 3769.66, 3769.66),
    ("DIEGO DE MELLO", "SERGIO GABRIEL DE MELLO", "2025-09-28", 12, 27300, 2100, 2100),
    ("DOUGLAS PICCINI DE OLIVEIRA", "MARINES PICCINI DE OLIVEIRA", "2026-05-22", 3, 0, 0, 0),
    ("EDIPO ALEXANDER PESSOA", "ARISSONIA DA SILVA", "2026-05-23", 3, 8800, 2200, 0),
    ("EDSON MOREIRA DE CASTILHO FILHO", "PREFEITURA DE MOREIRA SALES", "2025-12-02", 6, 28000, 4000, 4000),
    ("EVERTON GAMST INDRUSCAK", "CLAIR GAMST INDRUSCZAK", "2026-07-23", 3, 0, 0, 0),
    ("GABRIEL DOS SANTOS PETRY", "MARLI MILLER DOS SANTOS", "2026-05-21", 6, 14000, 2000, 0),
    ("GABRIEL SILVESTRO", "VALDEMAR SILVESTRO", "2026-06-06", 3, 10000, 2500, 0),
    ("GRÉGORY STEIMBACH CORDEIRO DOS SANTOS", "CARLA SABRINA STEIMBACH", "2026-07-01", 3, 10000, 2500, 0),
    ("IVO PINHEIRO", "DIRCEU OLIVEIRA PINHEIRO", "2026-07-02", 6, 0, 0, 0),
    ("JAIME AMARO", "MUNIC. DE ALTÔNIA / PR", "2026-02-08", 6, 24000, 4000, 0),
    ("JAKESON STEIN", "GERTRUT STEIN", "2026-08-13", 3, 10000, 2500, 0),
    ("JEAN CARLOS BERLANDA", "IVONE MARIA JUNGBLUTH", "2026-06-08", 3, 8000, 2000, 0),
    ("JHONATAN MARQUES SEGALLA", "LEUZINA COLOGNESI MARQUES", "2026-06-29", 3, 10000, 2500, 0),
    ("JOÃO FERREIRA DOS SANTOS", "FRANCISCO FERREIRA DOS SANTOS", "2026-07-08", 3, 10000, 2500, 0),
    ("JOÃO VITOR HOCHSCHEIDT MARTINS DE CARVALHO", "ANTONIO MARTINS DE CARVALHO", "2026-06-25", 3, 10000, 2500, 0),
    ("JONATAS SOARES DA ROSA", "SILVIA GRANDO", "2026-05-28", 6, 14000, 2000, 0),
    ("JOSÉ AUGUSTO APARECIDO ESTREGUE", "MARLI RODRIGUES SILVEIRA", "2026-07-11", 6, 0, 0, 0),
    ("KAIQUE WELTER SILVA DE SOUZA", "APARECIDA SILVA RODRIGUES", "2026-07-28", 3, 8800, 2200, 0),
    ("KAUAN RODRIGO SERGER MARQUES", "SIDINEIA MARQUES", "2026-05-18", 6, 17500, 2500, 0),
    ("LAÉRCIO BORNIA", "HERHIK DEHIMON BORNIA", "2026-08-01", 6, 14000, 2000, 0),
    ("LUCAS APARECIDO DE MORAES", "FERNANDA AP. GONC. BUENO DE FREITAS", "2026-08-06", 6, 0, 0, 0),
    ("LUCAS GABRIEL COGO", "JOAO PAULO COGO", "2026-05-08", 3, 8000, 2000, 0),
    ("LUCAS RODRIGUES RAMOS", "LENITA RODRIGUES", "2026-08-12", 3, 10000, 2500, 0),
    ("LUCAS SANTOS DE SOUZA", "MARCIO DE SOUZA", "2026-06-08", 3, 8000, 2000, 0),
    ("LUIZ CARLOS BENEDETTI", "ROSELI M. MARGAN BENEDETTI", "2026-05-22", 3, 10000, 2500, 0),
    ("MAICON DE MELO", "PATRICIA ROSANGELA DE MELO BONIFACIO", "2026-02-22", 6, 0, 0, 0),
    ("MARCELO PEREIRA SOUZA", "GILSON RICARDO DE SOUZA", "2026-05-30", 3, 12000, 3000, 0),
    ("MARCOS ALAN ALIONCIO", "MUNIC. DE BOA VISTA DA APARECIDA", "2026-05-21", 3, 6000, 1500, 0),
    ("MARLON BIANCHI ZANETTIN", "ANTONIO MARTINHO ZANETTIN", "2026-06-03", 3, 10000, 2500, 0),
    ("MAYCON MICHEL REGERT KOLLING", "MIRIAN CRISTINA REGERT", "2026-07-10", 6, 15300, 1500, 0),
    ("MIZAEL REIS DOS SANTOS", "GISLAINE FERREIRA RAMOS DOS SANTOS", "2026-08-17", 3, 8700, 1800, 0),
    ("PEDRO HENRIQUE ALCANTRA DA SILVA", "ADILSON INACIO DA SILVA", "2026-07-31", 6, 14000, 2000, 0),
    ("REGINALDO TELES FERREIRA", "REGINALDO TELES FERREIRA", "2026-06-03", 3, 0, 0, 0),
    ("RYAN ANDREW DALLO", "VALMIR DALLO", "2026-05-13", 3, 8000, 2000, 0),
    ("SEVÉLIO RUBEN ALVARES BEAL", "ALVAREZ BEAL", "2026-06-28", 3, 9100, 2500, 0),
    ("VLADECIR OSIRES IATCEKIW", "ISAIAS PAULO SHIROMA", "2026-06-08", 3, 10000, 2500, 0),
    ("VALMIR DOS REIS DA SILVA", "FUNDO M. SAUDE DE ALTONIA", "2026-05-29", 12, 65000, 5000, 0),
]


DADOS_RESIDENTES_RELATORIO = {
    "ADEVANIR MENEGHETE JUNIOR": ("10242462995", "ASSIS CHATEAUBRIAND"),
    "ANDRE HENRIQUE ALTMANN": ("11310097976", "MARECHAL CANDIDO RONDON"),
    "ANGEL MOISES PERALTA GONZALEZ": (None, "INCARNAÇÃO"),
    "CELSO DE LIMA": ("07759147970", "CAMPO BONITO"),
    "CICERO DE OLIVEIRA": ("44695004100", "GUAIRA"),
    "CLEOSMAR GOBETTI RIBEIRO GOMES": ("97293237887", "BOA VISTA DA APARECIDA"),
    "DIEGO DE MELLO": ("06120267956", "FRANCISCO BELTRAO"),
    "DOUGLAS PICCINI DE OLIVEIRA": ("10115415998", "JESUITAS"),
    "EDIPO ALEXANDER PESSOA": ("37470074813", "TUNEIRAS DO OESTE"),
    "EDSON MOREIRA DE CASTILHO FILHO": ("07463199916", "MOREIRA SALES"),
    "EVERTON GAMST INDRUSCAK": ("10235695904", "CAMPO BONITO"),
    "GABRIEL DOS SANTOS PETRY": ("13447775971", "ASSIS CHATEAUBRIAND"),
    "GABRIEL SILVESTRO": ("10114477973", "DOIS VIZINHOS"),
    "GREGORY STEIMBACH CORDEIRO DOS SANTOS": ("11179796950", "FRANCISCO BELTRAO"),
    "IVO PINHEIRO": ("64883345904", "CAMPO BONITO"),
    "JAIME AMARO": (None, "ALTONIA"),
    "JAKESON STEIN": ("07190430938", "PEROLA DO OESTE"),
    "JEAN CARLOS BERLANDA": ("01228008930", "MEDIANEIRA"),
    "JHONATAN MARQUES SEGALLA": ("10006142982", "JESUITAS"),
    "JOAO FERREIRA DOS SANTOS": ("74834630900", "NOVA AURORA"),
    "JOAO VITOR HOCHSCHEIDT MARTINS DE CARVALHO": ("15521674969", "TOLEDO"),
    "JONATAS SOARES DA ROSA": ("01632788063", "CAPANEMA"),
    "JOSE AUGUSTO APARECIDO ESTREGUE": ("07251313901", "CAMPO BONITO"),
    "KAIQUE WELTER SILVA DE SOUZA": ("46218182878", "CASCAVEL"),
    "KAUAN RODRIGO SERGER MARQUES": (None, "CURUPAYTY"),
    "LAERCIO BORNIA": ("78271851934", "IRACEMA DO ESTE"),
    "LUCAS APARECIDO DE MORAES": ("10073554928", "COLORADO"),
    "LUCAS GABRIEL COGO": ("09979575905", "SANTO ANTONIO DO SUDOESTE"),
    "LUCAS RODRIGUES RAMOS": ("09402309926", "TOLEDO"),
    "LUCAS SANTOS DE SOUZA": ("09653698974", "CAMPO MOURAO"),
    "LUIZ CARLOS BENEDETTI": ("60291184987", "NOVA PRATA DO IGUAÇU"),
    "MAICON DE MELO": ("37575737812", "BRASILANDIA DO SUL"),
    "MARCELO PEREIRA SOUZA": ("06429451950", "TOLEDO"),
    "MARCOS ALAN ALIONCIO": ("02732436917", "BOA VISTA DA APARECIDA"),
    "MARLON BIANCHI ZANETTIN": ("10353319937", "JESUITAS"),
    "MAYCON MICHEL REGERT KOLLING": ("13499878917", "SAO PEDRO DO IGUAÇU"),
    "MIZAEL REIS DOS SANTOS": ("04517487946", "CASCAVEL"),
    "PEDRO HENRIQUE ALCANTRA DA SILVA": ("07179404977", "CAMPO MOURAO"),
    "REGINALDO TELES FERREIRA": ("50759981434", "TOLEDO"),
    "RYAN ANDREW DALLO": ("08969622969", "DOIS VIZINHOS"),
    "SEVELIO RUBEN ALVARES BEAL": (None, "CIDADE DE LESTE"),
    "VLADECIR OSIRES IATCEKIW": ("02136702912", "FOZ DO IGUAÇU"),
    "VALMIR DOS REIS DA SILVA": (None, None),
}


def _chave_nome(nome):
    return (
        nome.upper()
        .replace("Á", "A").replace("À", "A").replace("Ã", "A")
        .replace("Â", "A").replace("É", "E").replace("Ê", "E")
        .replace("Í", "I").replace("Ó", "O").replace("Ô", "O")
        .replace("Õ", "O").replace("Ú", "U").replace("Ç", "C")
    )


def cadastrar_residentes():
    residentes = []
    for indice, (nome, *_) in enumerate(DADOS_INTERNACOES, start=1):
        cpf, cidade_origem = DADOS_RESIDENTES_RELATORIO[_chave_nome(nome)]
        cpf = cpf or f"PENDENTE-RESIDENTE-{indice:03d}"
        residentes.append(cadastrar_residente(nome, cpf, cidade_origem))
    return residentes


def cadastrar_responsaveis():
    return [
        cadastrar_responsavel(nome, f"PENDENTE-RESPONSAVEL-{indice:03d}", None, None)
        for indice, (_, nome, *_) in enumerate(DADOS_INTERNACOES, start=1)
    ]


def cadastrar_internacoes(residentes, responsaveis):
    internacoes = []
    for residente, responsavel, dados in zip(residentes, responsaveis, DADOS_INTERNACOES):
        _, _, data, periodo, contrato, acolhimento, mensalidade = dados
        resultado = cadastrar_internacao(
            residente_id=residente["id"], responsavel_id=responsavel["id"],
            data_acolhimento=data, periodo_tratamento=periodo,
            valor_contrato=round(contrato * CENTAVOS),
            valor_acolhimento=round(acolhimento * CENTAVOS),
            valor_mensalidade=round(mensalidade * CENTAVOS),
        )
        internacoes.append(_exigir_sucesso(resultado, "Cadastro da internação"))
    return internacoes


def gerar_todas_cobrancas(internacoes):
    for internacao in internacoes:
        _exigir_sucesso(gerar_cobrancas(internacao["id"]), "Geração das cobranças")


def _id_cobranca(internacao_id, numero_parcela):
    for cobranca in listar_cobrancas(internacao_id):
        if cobranca["numero_parcela"] == numero_parcela:
            return cobranca["id"]
    raise RuntimeError("Cobrança de teste não encontrada.")


def _registrar_recebimento(internacao_id, parcela, data, valor_reais, forma, observacao):
    resultado = registrar_recebimento(
        cobranca_id=_id_cobranca(internacao_id, parcela),
        data_pagamento=data, valor=valor_reais * CENTAVOS,
        forma_pagamento=forma, observacao=observacao,
    )
    return _exigir_sucesso(resultado, "Registro de recebimento")


def cadastrar_recebimentos(internacoes):
    """Não importa recebimentos enquanto a planilha não for sua fonte final."""


def cadastrar_financeiro():
    setores = {
        nome: _exigir_sucesso(cadastrar_setor(nome), "Cadastro de setor")["id"]
        for nome in ("Administração", "Cozinha", "Transporte", "Manutenção", "Alojamento")
    }
    tipos = {
        nome: _exigir_sucesso(cadastrar_tipo_despesa(nome), "Cadastro de tipo de despesa")["id"]
        for nome in ("Internet", "Alimentação", "Combustível", "Manutenção", "Energia elétrica", "Água", "Material de limpeza")
    }
    dados_despesas = [
        ("Internet", "Administração", "Internet", "Internet da clínica", "FIXA", True),
        ("Alimentação", "Cozinha", "Alimentação", "Compra de alimentos", "VARIAVEL", True),
        ("Combustível", "Transporte", "Combustível", "Combustível dos veículos", "VARIAVEL", True),
        ("Manutenção", "Manutenção", "Manutenção", "Reparos gerais da clínica", "EXTRAORDINARIA", False),
        ("Energia", "Administração", "Energia elétrica", "Conta de energia elétrica", "FIXA", True),
        ("Água", "Administração", "Água", "Conta de água", "FIXA", True),
    ]
    despesas = {}
    for chave, setor, tipo, descricao, natureza, recorrente in dados_despesas:
        despesas[chave] = _exigir_sucesso(
            cadastrar_despesa(setores[setor], tipos[tipo], descricao, natureza, recorrente),
            "Cadastro de despesa",
        )["id"]

    dados_contas = [
        ("Internet", "2026-09-10", 18000), ("Alimentação", "2026-09-05", 125000),
        ("Combustível", "2026-09-08", 85000), ("Manutenção", "2026-09-15", 230000),
        ("Energia", "2026-09-20", 45000), ("Água", "2026-09-25", 22000),
    ]
    contas = {
        chave: _exigir_sucesso(cadastrar_conta(despesas[chave], vencimento, valor), "Cadastro de conta")["id"]
        for chave, vencimento, valor in dados_contas
    }
    pagamentos_saida = [
        ("Internet", "2026-09-10", 9000, "PIX", "Pagamento parcial"),
        ("Combustível", "2026-09-08", 85000, "DINHEIRO", "Pagamento integral"),
        ("Energia", "2026-09-20", 20000, "PIX", "Primeira parcela"),
        ("Energia", "2026-09-22", 10000, "DINHEIRO", "Segunda parcela"),
    ]
    for chave, data, valor, forma, observacao in pagamentos_saida:
        _exigir_sucesso(
            registrar_pagamento_saida(contas[chave], data, valor, forma, observacao),
            "Registro de pagamento de saída",
        )
    _exigir_sucesso(cancelar_conta(contas["Manutenção"]), "Cancelamento da conta")


def mostrar_resumo(conn):
    print("\n=== RESUMO DE ENTRADAS ===")
    entradas = conn.execute("""
        SELECT r.nome, c.tipo, c.numero_parcela, c.valor, c.desconto,
               COALESCE(SUM(rc.valor), 0), c.status
        FROM cobrancas c
        INNER JOIN internacoes i ON i.id = c.internacao_id
        INNER JOIN residentes r ON r.id = i.residente_id
        LEFT JOIN recebimentos rc ON rc.cobranca_id = c.id
        GROUP BY c.id
        ORDER BY r.id, c.numero_parcela
    """)
    for nome, tipo, parcela, valor, desconto, pago, status in entradas:
        print({"residente": nome, "tipo": tipo, "parcela": parcela,
               "valor_devido": valor - desconto, "total_recebido": pago, "status": status})

    print("\n=== RESUMO DE SAÍDAS ===")
    saidas = conn.execute("""
        SELECT d.descricao, cp.data_vencimento, cp.valor,
               COALESCE(SUM(ps.valor), 0), cp.status
        FROM contas_pagar cp
        INNER JOIN despesas d ON d.id = cp.despesa_id
        LEFT JOIN pagamentos_saida ps ON ps.conta_pagar_id = cp.id
        GROUP BY cp.id
        ORDER BY cp.id
    """)
    for descricao, vencimento, valor, pago, status in saidas:
        print({"despesa": descricao, "vencimento": vencimento, "valor": valor,
               "total_pago": pago, "restante": valor - pago, "status": status})


def popular_banco():
    criar_tabelas()
    conn = conectar()
    try:
        limpar_banco()
        residentes = cadastrar_residentes()
        responsaveis = cadastrar_responsaveis()
        cadastrar_internacoes(residentes, responsaveis)
        mostrar_resumo(conn)
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("\n=== BANCO POPULADO COM SUCESSO ===")


if __name__ == "__main__":
    popular_banco()
