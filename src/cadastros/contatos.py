"""Contato principal atual é independente do responsável de cada contrato."""
from contextlib import closing
import json
from src.infraestrutura.banco import conectar


def preparar_schema(conn):
    conn.execute('''CREATE TABLE historico_contatos_principais (
        id INTEGER PRIMARY KEY AUTOINCREMENT, residente_id INTEGER NOT NULL REFERENCES residentes(id),
        responsavel_id INTEGER NOT NULL REFERENCES responsaveis(id), anteriores TEXT NOT NULL,
        motivo TEXT NOT NULL, registrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    # Não escolhe entre contatos legados ambíguos. Impede novas duplicidades.
    for evento in ('INSERT', 'UPDATE OF principal,residente_id'):
        sufixo = 'insert' if evento == 'INSERT' else 'update'
        conn.execute(f'''CREATE TRIGGER contato_principal_unico_{sufixo}
            BEFORE {evento} ON residente_responsavel
            WHEN NEW.principal=1 AND EXISTS(SELECT 1 FROM residente_responsavel
                WHERE residente_id=NEW.residente_id AND principal=1 AND id!=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Já existe contato principal. Use a escolha explícita do contato atual.'); END''')


def definir(residente_id, responsavel_id, motivo):
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError('Informe o motivo da escolha do contato principal.')
    with closing(conectar()) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if not conn.execute('SELECT 1 FROM residentes WHERE id=?', (residente_id,)).fetchone():
            raise ValueError('Residente não encontrado.')
        if not conn.execute('SELECT 1 FROM responsaveis WHERE id=? AND ativo=1', (responsavel_id,)).fetchone():
            raise ValueError('Selecione um responsável ativo.')
        anteriores = [r[0] for r in conn.execute('SELECT responsavel_id FROM residente_responsavel WHERE residente_id=? AND principal=1', (residente_id,))]
        conn.execute('UPDATE residente_responsavel SET principal=0 WHERE residente_id=?', (residente_id,))
        conn.execute('''INSERT INTO residente_responsavel(residente_id,responsavel_id,relacao,principal)
            VALUES(?,?,'Contato principal',1) ON CONFLICT(residente_id,responsavel_id) DO UPDATE SET principal=1''', (residente_id, responsavel_id))
        cur = conn.execute('INSERT INTO historico_contatos_principais(residente_id,responsavel_id,anteriores,motivo) VALUES(?,?,?,?)',
                           (residente_id, responsavel_id, json.dumps(anteriores), motivo.strip()))
        return {'sucesso': True, 'id': cur.lastrowid, 'residente_id': residente_id, 'responsavel_id': responsavel_id}
