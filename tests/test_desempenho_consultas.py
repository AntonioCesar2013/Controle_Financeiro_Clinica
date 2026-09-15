import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src.cantina.api_publica import dados_conferencia
from src.financeiro import caixa, contas_pagar
from src.infraestrutura import banco


class DesempenhoConsultas(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory(prefix="desempenho_clinica_")
        self.addCleanup(self.pasta.cleanup)
        caminho = Path(self.pasta.name) / "teste.db"
        self.patch_banco = patch.object(banco, "CAMINHO_BANCO", caminho)
        self.patch_banco.start()
        self.addCleanup(self.patch_banco.stop)
        banco.criar_tabelas()

    def test_indices_operacionais_sao_criados(self):
        with closing(banco.conectar()) as conexao:
            indices = {linha[0] for linha in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )}
        self.assertIn("idx_recebimentos_cobranca_data", indices)
        self.assertIn("idx_mov_carteira_carteira_data", indices)
        self.assertIn("idx_item_valores_vigencia", indices)

    def test_resumo_agregado_equivale_aos_detalhes(self):
        with closing(banco.conectar()) as conexao:
            conexao.execute("INSERT INTO setores(nome) VALUES ('Geral')")
            conexao.execute("INSERT INTO despesas(descricao,setor_id,natureza) VALUES ('Teste',1,'FIXA')")
            conexao.execute("INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status) VALUES (1,'2026-09-10',5000,'PAGA')")
            conexao.execute("INSERT INTO pagamentos_saida(conta_pagar_id,data_pagamento,valor,multa_juros,forma_pagamento) VALUES (1,'2026-09-10',5000,250,'PIX')")
            conexao.commit()
        resposta = caixa.resumo_com_movimentacoes("2026-09-01", "2026-09-30")
        self.assertEqual(resposta["total_saidas"], 5250)
        self.assertEqual(resposta["total_saidas"], sum(
            item["valor"] for item in resposta["movimentacoes"] if item["tipo"] == "SAIDA"
        ))

    def test_conferencia_calcula_residual_sem_varrer_por_carteira(self):
        with closing(banco.conectar()) as conexao:
            conexao.row_factory = sqlite3.Row
            conexao.execute("INSERT INTO residentes(nome,cpf,ativo) VALUES ('Teste','999',1)")
            conexao.execute("INSERT INTO carteiras(residente_id,saldo,ativo) VALUES (1,700,1)")
            conexao.execute("INSERT INTO movimentacoes_carteira(carteira_id,tipo,valor_total,data_movimentacao) VALUES (1,'CREDITO',1000,'2026-08-01')")
            conexao.execute("INSERT INTO movimentacoes_carteira(carteira_id,tipo,valor_total,data_movimentacao) VALUES (1,'COMPRA',300,'2026-09-01')")
            conexao.commit()
            resultado = dados_conferencia(conexao, "2026-09-01", "2026-09-30")
        self.assertEqual(resultado["saldo_abertura"], 1000)
        self.assertEqual(resultado["saldo_fechamento"], 700)
        self.assertEqual(resultado["compras"], 300)

    def test_contas_pagar_paginam_depois_dos_filtros_com_totais_separados(self):
        with closing(banco.conectar()) as conexao:
            conexao.execute("INSERT INTO setores(nome) VALUES ('Administração')")
            conexao.execute("INSERT INTO despesas(descricao,setor_id,natureza) VALUES ('Água',1,'FIXA')")
            conexao.executemany(
                "INSERT INTO contas_pagar(despesa_id,data_vencimento,valor,status) VALUES (1,?,?,?)",
                [(f"2026-09-{dia:02d}", dia * 100, "ABERTA") for dia in range(1, 8)],
            )
            conexao.commit()
        primeira = contas_pagar.listar_contas_paginadas(busca="agua", pagina=1, tamanho=3)
        segunda = contas_pagar.listar_contas_paginadas(busca="água", pagina=2, tamanho=3)
        self.assertEqual(primeira["total_registros"], 7)
        self.assertEqual(primeira["total_filtrado"], 7)
        self.assertEqual([r["id"] for r in primeira["linhas"]], [1, 2, 3])
        self.assertEqual([r["id"] for r in segunda["linhas"]], [4, 5, 6])
        self.assertEqual(primeira["totais_filtrados"]["valor"], 2800)


if __name__ == "__main__":
    unittest.main()
