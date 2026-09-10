"""Resultado persistente para reenvios, gravado junto com negócio e auditoria."""
import hashlib
import json
import re
from contextlib import closing

from src.infraestrutura import auditoria
from src.infraestrutura.banco import conectar
from src.infraestrutura.transacoes import ATUAL, Transacao, TransacaoInvalidada
from src.nucleo.migracoes import Migracao, aplicar_migracoes


class ConflitoOperacao(ValueError):
    pass


def _schema(conn):
    conn.execute('''CREATE TABLE operacoes_api (
        chave TEXT PRIMARY KEY, rota TEXT, assinatura TEXT,
        estado TEXT NOT NULL CHECK(estado IN ('CONFIRMADA','CANCELADA')),
        resposta TEXT, status_http INTEGER,
        registrada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')


def preparar_banco(conn):
    aplicar_migracoes(conn, [Migracao('infraestrutura', 1, _schema)])


def validar_chave(chave):
    if not isinstance(chave, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', chave):
        raise ValueError('Identificador da operação ausente ou inválido. Atualize o sistema e tente novamente.')
    return chave


def _abrir():
    conn = conectar()
    conn.execute('PRAGMA busy_timeout=5000')
    return conn


def _resposta(registro):
    return json.loads(registro[3]), registro[4], None


def executar(chave, rota, dados, funcao, colaborador=None, endereco_ip=None):
    validar_chave(chave)
    assinatura = hashlib.sha256(json.dumps([rota, dados], sort_keys=True, ensure_ascii=False,
                                          separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    with closing(_abrir()) as conn:
        conn.execute('BEGIN IMMEDIATE')
        anterior = conn.execute('SELECT rota,assinatura,estado,resposta,status_http FROM operacoes_api WHERE chave=?', (chave,)).fetchone()
        if anterior:
            conn.rollback()
            if anterior[2] == 'CANCELADA':
                raise ConflitoOperacao('Esta tentativa foi cancelada. Atualize a tela antes de iniciar outra operação.')
            if anterior[:2] != (rota, assinatura):
                raise ConflitoOperacao('O identificador já foi usado com outros dados. Verifique a operação pendente.')
            return _resposta(anterior)
        transacao = Transacao(conn)
        token = ATUAL.set(transacao)
        try:
            payload, status, cookie = funcao()
            if transacao.erro_banco is not None:
                raise transacao.erro_banco
            if transacao.invalidada and payload.get('sucesso'):
                raise TransacaoInvalidada('A operação foi invalidada antes da confirmação.')
            if status >= 400 or not payload.get('sucesso'):
                conn.rollback()
                return {**payload, 'estado_operacao': 'NAO_REALIZADA', 'operacao_id': chave}, status, cookie
            auditoria.registrar(
                'INCLUSAO' if status == 201 else 'ALTERACAO', rota.removeprefix('/api/'),
                payload.get('id') or payload.get('carteira_id'),
                {'operacao_id': chave, 'solicitacao': dados}, colaborador, endereco_ip,
            )
            payload = {**payload, 'estado_operacao': 'CONFIRMADA', 'operacao_id': chave}
            resposta = json.dumps(payload, ensure_ascii=False, allow_nan=False)
            conn.execute('INSERT INTO operacoes_api(chave,rota,assinatura,estado,resposta,status_http) VALUES(?,?,?,\'CONFIRMADA\',?,?)',
                         (chave, rota, assinatura, resposta, status))
            conn.commit()
            return payload, status, cookie
        except BaseException:
            conn.rollback()
            raise
        finally:
            ATUAL.reset(token)


def consultar(chave):
    validar_chave(chave)
    with closing(_abrir()) as conn:
        # Espera uma gravação em andamento antes de informar o resultado.
        conn.execute('BEGIN IMMEDIATE')
        r = conn.execute('SELECT estado,rota,resposta,registrada_em FROM operacoes_api WHERE chave=?', (chave,)).fetchone()
        conn.rollback()
        return {'operacao_id': chave, 'estado': r[0] if r else 'NAO_LOCALIZADA',
                'rota': r[1] if r else None, 'resultado': json.loads(r[2]) if r and r[2] else None,
                'registrada_em': r[3] if r else None}


def cancelar(chave):
    validar_chave(chave)
    with closing(_abrir()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        r = conn.execute('SELECT estado,resposta FROM operacoes_api WHERE chave=?', (chave,)).fetchone()
        if r:
            return {'sucesso': True, 'estado': r[0], 'resultado': json.loads(r[1]) if r[1] else None}
        # Uma solicitação atrasada com esta chave será recusada, mesmo que
        # chegue depois da consulta. Cancelar aqui não estorna lançamentos.
        conn.execute("INSERT INTO operacoes_api(chave,estado) VALUES(?,'CANCELADA')", (chave,))
        return {'sucesso': True, 'estado': 'CANCELADA', 'resultado': None}
