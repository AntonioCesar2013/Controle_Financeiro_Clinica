"""Uma transação por operação HTTP, compartilhada pelas rotinas legadas.

Cada chamada de conectar() recebe uma conexão emprestada com row_factory
própria. commit/close locais não encerram a transação do chamador; rollback
ou uma saída excepcional invalidam toda a operação. Fora deste contexto,
conectar() continua retornando uma conexão SQLite normal.
"""
from contextvars import ContextVar
import sqlite3


ATUAL = ContextVar('transacao_operacao', default=None)


class TransacaoInvalidada(RuntimeError):
    pass


class Transacao:
    def __init__(self, conexao):
        self.conexao = conexao
        self.invalidada = False
        self.erro_banco = None

    def emprestar(self):
        return ConexaoEmprestada(self)


class CursorEmprestado:
    def __init__(self, conexao):
        self.conexao = conexao
        self.cursor = conexao.transacao.conexao.cursor()
        self.cursor.row_factory = conexao.row_factory

    def execute(self, sql, parametros=()):
        self.conexao._verificar()
        # Os módulos já abrem BEGIN ao iniciar sua rotina. O BEGIN externo
        # foi adquirido antes de qualquer leitura da chave de idempotência.
        if sql.strip().rstrip(';').upper() in ('BEGIN', 'BEGIN IMMEDIATE', 'BEGIN TRANSACTION', 'BEGIN DEFERRED'):
            return self
        try:
            self.cursor.execute(sql, parametros)
        except sqlite3.Error as erro:
            self.conexao.transacao.erro_banco = erro
            raise
        return self

    def executemany(self, sql, parametros):
        self.conexao._verificar()
        try:
            self.cursor.executemany(sql, parametros)
        except sqlite3.Error as erro:
            self.conexao.transacao.erro_banco = erro
            raise
        return self

    def __getattr__(self, nome):
        return getattr(self.cursor, nome)

    def __iter__(self):
        return iter(self.cursor)


class ConexaoEmprestada:
    def __init__(self, transacao):
        self.transacao = transacao
        self.row_factory = None
        self.fechada = False

    def _verificar(self):
        if self.fechada:
            raise sqlite3.ProgrammingError('Conexão local já encerrada.')
        if self.transacao.invalidada:
            raise TransacaoInvalidada('A operação deve ser revertida.')

    def cursor(self):
        self._verificar()
        return CursorEmprestado(self)

    def execute(self, sql, parametros=()):
        return self.cursor().execute(sql, parametros)

    def executemany(self, sql, parametros):
        return self.cursor().executemany(sql, parametros)

    def commit(self):
        self._verificar()

    def rollback(self):
        self.transacao.invalidada = True

    def close(self):
        self.fechada = True

    def __enter__(self):
        self._verificar()
        return self

    def __exit__(self, tipo, erro, traceback):
        if tipo:
            self.rollback()
        return False

