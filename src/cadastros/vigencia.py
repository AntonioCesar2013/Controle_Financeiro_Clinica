"""Consulta de vigência histórica sem alterar o estado atual do residente."""
from datetime import date
from src.financeiro.api_publica import data_final_contrato


def possui_internacao_vigente(conexao, residente_id, data_referencia):
    referencia = date.fromisoformat(data_referencia)
    for inicio, periodo, encerrada, modalidade in conexao.execute(
        """SELECT data_acolhimento,periodo_tratamento,encerrada_em,modalidade
           FROM internacoes WHERE residente_id=? AND status!='CANCELADA'""", (residente_id,)):
        if referencia < date.fromisoformat(inicio):
            continue
        # Mesma convenção do status: a saída antecipada já encerra esse dia.
        if encerrada and referencia >= date.fromisoformat(encerrada):
            continue
        if modalidade == 'VOLUNTARIO' or referencia <= data_final_contrato(inicio, periodo):
            return True
    return False
