"""Vigências e decisões explícitas para competências recorrentes."""


def aplicar(conn):
    conn.execute('''CREATE TABLE recorrencias_reajustes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recorrencia_id INTEGER NOT NULL REFERENCES recorrencias_despesas(id),
        valor INTEGER NOT NULL CHECK(typeof(valor)='integer' AND valor>0),
        data_inicio_vigencia TEXT NOT NULL,
        motivo TEXT NOT NULL,
        criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(recorrencia_id,data_inicio_vigencia))''')
    conn.execute('''CREATE TABLE recorrencias_competencias_dispensadas (
        recorrencia_id INTEGER NOT NULL REFERENCES recorrencias_despesas(id),
        data_vencimento TEXT NOT NULL,
        motivo TEXT NOT NULL,
        criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(recorrencia_id,data_vencimento))''')
