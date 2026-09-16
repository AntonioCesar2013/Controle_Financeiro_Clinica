"""Consulta de vigência histórica sem alterar o estado atual do residente."""
from datetime import date
from src.financeiro.api_publica import data_final_contrato


def ultimo_dia_vigente(inicio, periodo, encerrada=None, modalidade=None):
    """Término natural é inclusivo; saída antecipada é exclusiva."""
    if encerrada:
        from datetime import timedelta
        return date.fromisoformat(encerrada) - timedelta(days=1)
    return date.max if modalidade == 'VOLUNTARIO' else data_final_contrato(inicio, periodo)


def possui_internacao_vigente(conexao, residente_id, data_referencia):
    referencia = date.fromisoformat(data_referencia)
    for inicio, periodo, encerrada, modalidade in conexao.execute(
        """SELECT data_acolhimento,periodo_tratamento,encerrada_em,modalidade
           FROM internacoes WHERE residente_id=? AND status!='CANCELADA'""", (residente_id,)):
        if referencia < date.fromisoformat(inicio):
            continue
        if referencia <= ultimo_dia_vigente(inicio, periodo, encerrada, modalidade):
            return True
    return False
