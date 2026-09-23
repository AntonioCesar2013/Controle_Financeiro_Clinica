"""Inspeção agregada em cópia temporária. Origem aberta apenas mode=ro."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.infraestrutura import banco
from src.infraestrutura.backup.config import BackupConfig


def main():
    result = {}
    source = ROOT / 'dados' / 'clinica.db'
    with tempfile.TemporaryDirectory(prefix='auditoria_producao_') as tmp:
        dest = Path(tmp) / 'copia.db'
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as src, closing(sqlite3.connect(dest)) as dst:
            src.backup(dst)
        with closing(sqlite3.connect(dest)) as conn:
            result['integridade'] = conn.execute('PRAGMA integrity_check').fetchall()
            result['violacoes_fk_antes'] = len(conn.execute('PRAGMA foreign_key_check').fetchall())
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            counts = {t: conn.execute('SELECT COUNT(*) FROM "' + t.replace('"','""') + '"').fetchone()[0] for t in tables}
            result['migracoes_antes'] = conn.execute('SELECT modulo,MAX(versao) FROM migracoes_schema GROUP BY modulo').fetchall()
        with patch.object(banco, 'CAMINHO_BANCO', dest):
            banco.criar_tabelas()
            banco.criar_tabelas()
        with closing(sqlite3.connect(dest)) as conn:
            result['integridade_apos_migracoes'] = conn.execute('PRAGMA integrity_check').fetchall()
            result['violacoes_fk_depois'] = len(conn.execute('PRAGMA foreign_key_check').fetchall())
            result['contagens_alteradas'] = {t: [n, conn.execute('SELECT COUNT(*) FROM "' + t.replace('"','""') + '"').fetchone()[0]] for t,n in counts.items() if t != 'migracoes_schema' and n != conn.execute('SELECT COUNT(*) FROM "' + t.replace('"','""') + '"').fetchone()[0]}
            result['migracoes_depois'] = conn.execute('SELECT modulo,MAX(versao) FROM migracoes_schema GROUP BY modulo').fetchall()
            queries = {
                'cobrancas_saldo_negativo': 'SELECT COUNT(*) FROM cobrancas c WHERE c.valor-c.desconto < COALESCE((SELECT SUM(r.valor) FROM recebimentos_liquidos r WHERE r.cobranca_id=c.id),0)',
                'cobrancas_status_divergente': "SELECT COUNT(*) FROM cobrancas c WHERE c.status != CASE WHEN c.valor-c.desconto=0 THEN 'DESCONTADA' WHEN COALESCE((SELECT SUM(valor) FROM recebimentos_liquidos r WHERE r.cobranca_id=c.id),0)=c.valor-c.desconto THEN 'PAGA' WHEN COALESCE((SELECT SUM(valor) FROM recebimentos_liquidos r WHERE r.cobranca_id=c.id),0)>0 THEN 'PARCIAL' ELSE 'ABERTA' END",
                'contas_canceladas_com_pagamento': "SELECT COUNT(*) FROM contas_pagar c WHERE c.status='CANCELADA' AND EXISTS(SELECT 1 FROM pagamentos_saida p WHERE p.conta_pagar_id=c.id)",
                'contas_saldo_negativo': 'SELECT COUNT(*) FROM contas_pagar c WHERE c.valor-c.desconto < COALESCE((SELECT SUM(p.valor) FROM pagamentos_saida p WHERE p.conta_pagar_id=c.id),0)',
                'estoque_negativo': 'SELECT COUNT(*) FROM itens_cantina WHERE estoque_atual<0',
                'administracao_saldo_negativo': 'SELECT COUNT(*) FROM itens_administracao WHERE quantidade<0',
            }
            result['consistencia'] = {k: conn.execute(v).fetchone()[0] for k,v in queries.items()}
    cfg = BackupConfig()
    data = cfg.load()
    result['backup'] = {k:data[k] for k in ('backup_enabled','interval_hours','r2_enabled','drive_enabled')}
    result['backup']['pasta_configurada'] = bool(data['backup_directory'])
    result['backup']['arquivo_config_existe'] = cfg.path.exists()
    statuspath = cfg.directory / 'backup-status.json'
    if statuspath.exists():
        state = json.loads(statuspath.read_text(encoding='utf-8'))
        result['backup']['last_success'] = state.get('last_success')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
