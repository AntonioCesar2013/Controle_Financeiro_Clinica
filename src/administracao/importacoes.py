"""Importacoes administrativas com validacao previa e gravacao atomica."""
from contextlib import closing
from datetime import date

from src.financeiro.moeda import reais_para_centavos
from src.infraestrutura.banco import conectar
from src.nucleo.validacao import inteiro


TIPOS_COBRANCA = {"ACOLHIMENTO", "MENSALIDADE", "OUTRO"}
MAXIMO_LINHAS = 1000


def _texto(valor, nome, limite=100):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"Informe {nome}.")
    texto = valor.strip().upper()
    if len(texto) > limite:
        raise ValueError(f"{nome.capitalize()} deve ter ate {limite} caracteres.")
    return texto


def _data(valor):
    try:
        if not isinstance(valor, str) or date.fromisoformat(valor.strip()).isoformat() != valor.strip():
            raise ValueError
    except ValueError:
        raise ValueError("Data de vencimento deve estar no formato AAAA-MM-DD.") from None
    return valor.strip()


def _normalizar_linha(linha, numero_linha):
    if not isinstance(linha, dict):
        raise ValueError("A linha deve conter colunas validas.")
    internacao_id = inteiro(linha.get("internacao_id"), "internacao_id", 1)
    numero_parcela = inteiro(linha.get("numero_parcela"), "numero_parcela", 0)
    tipo = _texto(linha.get("tipo"), "tipo")
    if tipo not in TIPOS_COBRANCA:
        raise ValueError("Tipo deve ser ACOLHIMENTO, MENSALIDADE ou OUTRO.")
    vencimento = _data(linha.get("data_vencimento"))
    valor = reais_para_centavos(linha.get("valor"))
    desconto = reais_para_centavos(linha.get("desconto", 0))
    if valor <= 0:
        raise ValueError("Valor deve ser maior que zero.")
    if desconto < 0 or desconto > valor:
        raise ValueError("Desconto deve estar entre zero e o valor da cobranca.")
    return {
        "linha": numero_linha,
        "internacao_id": internacao_id,
        "numero_parcela": numero_parcela,
        "tipo": tipo,
        "data_vencimento": vencimento,
        "valor": valor,
        "desconto": desconto,
        "status": "DESCONTADA" if desconto == valor else "ABERTA",
    }


def processar_contas_receber(linhas, confirmar=False):
    if not isinstance(linhas, list) or not linhas:
        raise ValueError("O arquivo deve conter ao menos uma linha de dados.")
    if len(linhas) > MAXIMO_LINHAS:
        raise ValueError(f"O arquivo aceita no maximo {MAXIMO_LINHAS} linhas por importacao.")

    normalizadas, erros, chaves_arquivo = [], [], set()
    for indice, linha in enumerate(linhas, start=2):
        try:
            item = _normalizar_linha(linha, indice)
            chave = (item["internacao_id"], item["numero_parcela"])
            if chave in chaves_arquivo:
                raise ValueError("Internacao e numero da parcela repetidos no arquivo.")
            chaves_arquivo.add(chave)
            normalizadas.append(item)
        except ValueError as erro:
            erros.append({"linha": indice, "erro": str(erro)})

    with closing(conectar()) as conn:
        conn.row_factory = None
        internacoes = {
            linha[0]: linha[1]
            for linha in conn.execute(
                """SELECT i.id, r.nome FROM internacoes i
                   JOIN residentes r ON r.id=i.residente_id
                   WHERE i.id IN ({})""".format(",".join("?" for _ in normalizadas) or "NULL"),
                [item["internacao_id"] for item in normalizadas],
            )
        }
        existentes = {
            (linha[0], linha[1])
            for linha in conn.execute("SELECT internacao_id,numero_parcela FROM cobrancas")
        }
        prontas = []
        for item in normalizadas:
            if item["internacao_id"] not in internacoes:
                erros.append({"linha": item["linha"], "erro": "Internacao nao encontrada."})
                continue
            prontas.append({
                **item,
                "residente_nome": internacoes[item["internacao_id"]],
                "duplicada": (item["internacao_id"], item["numero_parcela"]) in existentes,
            })

        if confirmar and erros:
            raise ValueError("Corrija os erros do arquivo antes de confirmar a importacao.")

        novas = [item for item in prontas if not item["duplicada"]]
        if confirmar and novas:
            conn.execute("BEGIN IMMEDIATE")
            conn.executemany(
                """INSERT INTO cobrancas
                   (internacao_id,numero_parcela,tipo,data_vencimento,valor,desconto,status)
                   VALUES(?,?,?,?,?,?,?)""",
                [(item["internacao_id"], item["numero_parcela"], item["tipo"],
                  item["data_vencimento"], item["valor"], item["desconto"], item["status"])
                 for item in novas],
            )
            conn.commit()

    return {
        "sucesso": True,
        "modo": "IMPORTACAO" if confirmar else "PREVIA",
        "total": len(linhas),
        "validas": len(prontas),
        "novas": len(novas),
        "duplicadas": sum(1 for item in prontas if item["duplicada"]),
        "importadas": len(novas) if confirmar else 0,
        "erros": sorted(erros, key=lambda item: item["linha"]),
        "linhas": prontas[:100],
    }
