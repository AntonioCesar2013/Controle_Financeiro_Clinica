"""Benchmark reproduzível das consultas otimizadas, sempre em banco descartável.

Uso: python -m src.scripts.benchmark_desempenho --volumes 1000 10000 100000
"""

import argparse
import json
import sqlite3
import tempfile
import time
from pathlib import Path


def medir(funcao, repeticoes=5):
    tempos = []
    resultado = None
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resultado = funcao()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return {"frio_ms": round(tempos[0], 3), "mediana_quente_ms": round(sorted(tempos[1:])[len(tempos[1:]) // 2], 3),
            "resultado": resultado}


def preparar(caminho, volume):
    conn = sqlite3.connect(caminho)
    conn.executescript('''
        CREATE TABLE contas(id INTEGER PRIMARY KEY, valor INTEGER, desconto INTEGER, status TEXT, vencimento TEXT);
        CREATE TABLE pagamentos(id INTEGER PRIMARY KEY, conta_id INTEGER, valor INTEGER, data TEXT);
        CREATE TABLE carteiras(id INTEGER PRIMARY KEY, saldo INTEGER);
        CREATE TABLE movimentos(id INTEGER PRIMARY KEY, carteira_id INTEGER, tipo TEXT, valor INTEGER, data TEXT, estornada INTEGER);
    ''')
    carteiras = max(10, min(500, volume // 20))
    conn.executemany("INSERT INTO carteiras VALUES(?,?)", ((i, 0) for i in range(1, carteiras + 1)))
    conn.executemany("INSERT INTO contas VALUES(?,?,?,?,?)", ((i, 10000, 0, 'ABERTA', f'2026-{i % 12 + 1:02d}-15') for i in range(1, volume + 1)))
    conn.executemany("INSERT INTO pagamentos VALUES(?,?,?,?)", ((i, i, 2500, f'2026-{i % 12 + 1:02d}-10') for i in range(1, volume + 1)))
    conn.executemany("INSERT INTO movimentos VALUES(?,?,?,?,?,?)", (
        (i, i % carteiras + 1, 'CREDITO' if i % 3 == 0 else 'COMPRA', 100 + i % 900,
         f'2026-{i % 12 + 1:02d}-{i % 28 + 1:02d}', int(i % 19 == 0)) for i in range(1, volume + 1)
    ))
    conn.execute("UPDATE carteiras SET saldo=(SELECT COALESCE(SUM(CASE WHEN estornada=1 THEN 0 WHEN tipo='CREDITO' THEN valor ELSE -ABS(valor) END),0) FROM movimentos WHERE carteira_id=carteiras.id)")
    conn.commit()
    return conn


def executar(volume, somente_atual=False):
    with tempfile.TemporaryDirectory(prefix="benchmark_clinica_") as pasta:
        conn = preparar(Path(pasta) / "massa.db", volume)
        def dashboard_anterior():
            contas = conn.execute("SELECT id FROM contas WHERE status!='CANCELADA'").fetchall()
            return sum(conn.execute("SELECT c.valor-c.desconto-COALESCE(SUM(p.valor),0) FROM contas c LEFT JOIN pagamentos p ON p.conta_id=c.id WHERE c.id=?", (row[0],)).fetchone()[0] for row in contas)
        def dashboard_atual():
            return conn.execute("SELECT COALESCE(SUM(restante),0) FROM (SELECT c.id,c.valor-c.desconto-COALESCE(SUM(p.valor),0) restante FROM contas c LEFT JOIN pagamentos p ON p.conta_id=c.id WHERE c.status!='CANCELADA' GROUP BY c.id)").fetchone()[0]
        def carteiras_anterior():
            todos = conn.execute("SELECT carteira_id,tipo,valor,estornada FROM movimentos").fetchall()
            return sum(sum(0 if m[3] else (m[2] if m[1]=='CREDITO' else -abs(m[2])) for m in todos if m[0] == carteira[0]) for carteira in conn.execute("SELECT id FROM carteiras"))
        def carteiras_atual():
            return conn.execute("SELECT COALESCE(SUM(CASE WHEN estornada=1 THEN 0 WHEN tipo='CREDITO' THEN valor ELSE -ABS(valor) END),0) FROM movimentos").fetchone()[0]
        resultado = {"volume": volume, "carteiras": conn.execute("SELECT COUNT(*) FROM carteiras").fetchone()[0],
                     "dashboard_depois": medir(dashboard_atual), "carteiras_depois": medir(carteiras_atual)}
        if not somente_atual:
            resultado.update(dashboard_antes=medir(dashboard_anterior), carteiras_antes=medir(carteiras_anterior))
        conn.close()
        return resultado


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--volumes", nargs="+", type=int, default=[1000, 10000, 100000])
    parser.add_argument("--somente-atual", action="store_true", help="Evita o algoritmo legado em massas muito grandes.")
    args = parser.parse_args()
    print(json.dumps([executar(volume, args.somente_atual) for volume in args.volumes], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
