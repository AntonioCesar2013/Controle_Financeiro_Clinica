import json
import mimetypes
import secrets
import threading
import webbrowser
from datetime import date
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.infraestrutura import auditoria
from src.financeiro import caixa
from src.cantina import vendas as cantina
from src.financeiro import configuracoes_financeiras
from src.financeiro import contas_pagar
from src.financeiro import contas_receber
from src.cadastros import convenios
from src.financeiro import despesas
from src.cantina import produtos as itens
from src.interface import relatorios
from src.interface import extrato_residente
from src.financeiro import recibos
from src.financeiro import pagamentos
from src.financeiro import recebimentos
from src.financeiro.moeda import reais_para_centavos
from src.financeiro.estornos import historico, historico_ajustes
from src.cadastros.internacoes import cancelar_agendamento
from src.infraestrutura import sincronizacao_nuvem
from src.infraestrutura.banco import criar_tabelas
from src.infraestrutura.backup_banco import criar_backup_diario
from src.infraestrutura.configuracao_instalacao import somente_leitura
from src.cadastros.colaboradores import (
    autenticar_colaborador, cadastrar_colaborador, editar_colaborador,
    possui_colaboradores, redefinir_senha,
)
from src.interface.consultas_interface import (
    listar_carteiras,
    listar_colaboradores,
    listar_internacoes,
    listar_residentes,
    listar_responsaveis,
)
from src.cadastros.residentes import cadastrar_residente, editar_residente
from src.cadastros.responsaveis import cadastrar_responsavel, editar_responsavel
from src.cadastros.internacoes import (
    alterar_responsavel_principal, cadastrar_internacao_com_cobrancas, encerrar_internacao,
    sincronizar_status_residentes,
)
from src.financeiro.cobrancas import aplicar_desconto, gerar_cobrancas


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
RAIZ_FRONTEND = RAIZ_PROJETO / "frontend"
SESSOES = {}
LOCK_SESSOES = threading.Lock()


def _parametro(query, nome, padrao=None):
    valores = query.get(nome)
    return valores[0] if valores else padrao


def _centavos(valor):
    try:
        return reais_para_centavos(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError("Valor financeiro inválido.") from erro


def _dashboard():
    hoje = date.today()
    resumo = caixa.resumo_mensal(hoje.year, hoje.month)
    receber = contas_receber.listar_cobrancas_consolidadas(data_referencia=hoje.isoformat())
    pagar = contas_pagar.listar_contas()
    total_receber = sum(conta["saldo_restante"] for conta in receber if conta["status"] not in ("PAGA", "DESCONTADA"))
    total_pagar = sum(
        contas_pagar.calcular_total_pago(conta["id"])["restante"]
        for conta in pagar
        if conta["status"] != "CANCELADA"
    )
    movimentacoes = caixa.listar_movimentacoes()
    return {
        **resumo,
        "total_receber": total_receber,
        "total_pagar": total_pagar,
        "movimentacoes_recentes": list(reversed(movimentacoes[-10:])),
    }


def _listar_contas_pagar(status=None, inicio=None, fim=None):
    resultado = []
    for conta in contas_pagar.listar_contas(status, inicio, fim):
        resumo = contas_pagar.calcular_total_pago(conta["id"])
        resultado.append({**conta, "total_pago": resumo.get("total_pago", 0), "restante": resumo.get("restante", conta["valor"])})
    return resultado


class Requisicao(BaseHTTPRequestHandler):
    server_version = "ClinicaHTTP/1.0"

    def do_GET(self):
        rota = urlparse(self.path)
        if rota.path == "/api/auth/status":
            return self._json({"configurado": possui_colaboradores(), "autenticado": self._sessao() is not None})
        if rota.path.startswith("/api/"):
            # TESTES: reative estas duas linhas para proteger novamente as rotas GET.
            # if self._sessao() is None:
            #     return self._json({"erro": "Sessão não autenticada."}, HTTPStatus.UNAUTHORIZED)
            return self._get_api(rota.path, parse_qs(rota.query))
        return self._arquivo_estatico(rota.path)

    def do_POST(self):
        rota = urlparse(self.path).path
        dados = self._corpo_json()
        if dados is None:
            return
        self._rota_auditoria = rota
        self._dados_auditoria = dados
        self._auditoria_registrada = False
        if rota == "/api/auth/setup":
            if possui_colaboradores():
                return self._json({"erro": "O primeiro acesso já foi configurado."}, HTTPStatus.CONFLICT)
            resultado = cadastrar_colaborador(dados.get("nome"), dados.get("cpf"), dados.get("senha"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/auth/login":
            colaborador = autenticar_colaborador(dados.get("cpf"), dados.get("senha"))
            if colaborador is None:
                return self._json({"erro": "CPF ou senha inválidos."}, HTTPStatus.UNAUTHORIZED)
            token = secrets.token_urlsafe(32)
            with LOCK_SESSOES:
                SESSOES[token] = colaborador
            return self._json({"sucesso": True, "colaborador": colaborador}, cookie=f"sessao={token}; HttpOnly; SameSite=Strict; Path=/")
        if rota == "/api/auth/logout":
            token = self._token_sessao()
            with LOCK_SESSOES:
                SESSOES.pop(token, None)
            return self._json({"sucesso": True}, cookie="sessao=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        if rota == "/api/sincronizacao/publicar":
            return self._resultado_operacao(sincronizacao_nuvem.publicar_versao(), criado=False)
        if rota == "/api/sincronizacao/atualizar":
            return self._resultado_operacao(sincronizacao_nuvem.atualizar_versao_local(), criado=False)
        if somente_leitura():
            return self._json(
                {"sucesso": False, "erro": "Esta instalação está configurada somente para leitura."},
                HTTPStatus.FORBIDDEN,
            )
        # TESTES: reative estas duas linhas para proteger novamente as rotas POST.
        # if self._sessao() is None:
        #     return self._json({"erro": "Sessão não autenticada."}, HTTPStatus.UNAUTHORIZED)
        campos_monetarios = {
            "/api/itens": ["valor"], "/api/itens/precos": ["valor"],
            "/api/itens/estoque": ["custo_unitario"], "/api/carteiras": ["saldo_inicial"],
            "/api/carteiras/credito": ["valor"], "/api/carteiras/movimentacoes/corrigir": ["valor"],
        }
        try:
            dados = dict(dados)
            for campo in campos_monetarios.get(rota, []):
                if campo == "custo_unitario" and dados.get(campo) in (None, ""):
                    dados[campo] = None
                else:
                    dados[campo] = _centavos(dados.get(campo))
        except (TypeError, ValueError) as erro:
            return self._json({"sucesso": False, "erro": str(erro)}, HTTPStatus.BAD_REQUEST)
        if rota == "/api/residentes":
            resultado = cadastrar_residente(dados.get("nome"), dados.get("cpf"), dados.get("cidade_origem"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/recibos":
            try:
                return self._json({"sucesso": True, "dados": recibos.gerar(dados.get("recebimento_id"))})
            except ValueError as erro:
                return self._json({"sucesso": False, "erro": str(erro)}, HTTPStatus.BAD_REQUEST)
        if rota == "/api/responsaveis":
            resultado = cadastrar_responsavel(dados.get("nome"), dados.get("cpf"), dados.get("telefone"), dados.get("email"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/internacoes":
            try:
                resultado = cadastrar_internacao_com_cobrancas(
                    dados.get("residente_id"), dados.get("responsavel_id"), dados.get("data_acolhimento"),
                    dados.get("periodo_tratamento"), _centavos(dados.get("valor_contrato")),
                    _centavos(dados.get("valor_acolhimento")), _centavos(dados.get("valor_mensalidade")),
                    dados.get("modalidade", "PARTICULAR"), dados.get("convenio_id"),
                    dados.get("servicos_voluntario"),
                )
            except ValueError as erro:
                return self._json({"sucesso": False, "erro": str(erro)}, HTTPStatus.BAD_REQUEST)
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/convenios":
            try:
                resultado = convenios.cadastrar_convenio(
                    dados.get("nome"), _centavos(dados.get("valor_diaria")), dados.get("ativo", 1)
                )
            except ValueError as erro:
                resultado = {"sucesso": False, "erro": str(erro)}
            return self._resultado_operacao(resultado)
        if rota == "/api/colaboradores":
            resultado = cadastrar_colaborador(dados.get("nome"), dados.get("cpf"), dados.get("senha"), dados.get("status", "ATIVO"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/itens":
            resultado = itens.cadastrar_produto(
                dados.get("nome"), dados.get("valor"), dados.get("estoque_inicial", 0),
                dados.get("estoque_minimo", 0), dados.get("codigo_barras"),
                dados.get("descricao"), dados.get("categoria"),
                dados.get("unidade_medida", "UN"), dados.get("ativo", 1),
                dados.get("data_inicio_valor"),
            )
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/cantina/vendas":
            resultado = cantina.registrar_venda(dados.get("carteira_id"), dados.get("item_id"), dados.get("quantidade", 1), dados.get("data_movimentacao"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/cantina/checkout":
            resultado = cantina.registrar_compra(dados.get("carteira_id"), dados.get("produtos"), dados.get("data_movimentacao"))
            return self._resultado_operacao(resultado)
        if rota == "/api/cantina/vendas/estornar":
            return self._resultado_operacao(cantina.estornar_compra(dados.get("venda_id"), dados.get("motivo")), criado=False)
        if rota == "/api/carteiras":
            resultado = cantina.criar_carteira(dados.get("residente_id"), dados.get("saldo_inicial", 0))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/carteiras/credito":
            resultado = cantina.adicionar_credito(dados.get("carteira_id"), dados.get("valor"), dados.get("data_movimentacao"))
            return self._json(resultado, HTTPStatus.CREATED if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)
        if rota == "/api/carteiras/status":
            return self._resultado_operacao(cantina.alterar_status_carteira(dados.get("carteira_id"), dados.get("ativo")), criado=False)
        if rota == "/api/carteiras/movimentacoes/estornar":
            return self._resultado_operacao(cantina.estornar_movimentacao(dados.get("movimentacao_id"), dados.get("motivo")), criado=False)
        if rota == "/api/carteiras/movimentacoes/corrigir":
            return self._resultado_operacao(cantina.corrigir_credito(dados.get("movimentacao_id"), dados.get("valor"), dados.get("data_movimentacao"), dados.get("motivo")), criado=False)
        if rota == "/api/residentes/editar":
            return self._resultado_operacao(editar_residente(dados.get("id"), dados.get("nome"), dados.get("cpf"), dados.get("cidade_origem")), criado=False)
        if rota == "/api/responsaveis/editar":
            return self._resultado_operacao(editar_responsavel(dados.get("id"), dados.get("nome"), dados.get("cpf"), dados.get("telefone"), dados.get("email"), dados.get("ativo", 1)), criado=False)
        if rota == "/api/internacoes/cancelar":
            return self._resultado_operacao(cancelar_agendamento(dados.get("id"), dados.get("motivo")))
        if rota == "/api/internacoes/encerrar":
            return self._resultado_operacao(encerrar_internacao(dados.get("id"), dados.get("data_encerramento"), dados.get("motivo"), str(dados.get("autorizar_ajuste_desconto", "")).lower() in ("1", "true")), criado=False)
        if rota == "/api/internacoes/responsavel":
            return self._resultado_operacao(alterar_responsavel_principal(dados.get("id"), dados.get("responsavel_id")), criado=False)
        if rota == "/api/itens/editar":
            return self._resultado_operacao(itens.editar_produto(
                dados.get("id"), dados.get("nome"), dados.get("codigo_barras"), dados.get("descricao"),
                dados.get("categoria"), dados.get("unidade_medida", "UN"), dados.get("estoque_minimo", 0), dados.get("ativo", 1),
            ), criado=False)
        if rota == "/api/itens/estoque":
            return self._resultado_operacao(itens.ajustar_estoque(
                dados.get("item_id"), dados.get("quantidade"), dados.get("motivo"),
                dados.get("data_movimentacao"), dados.get("tipo"), dados.get("custo_unitario"),
                dados.get("fornecedor"), dados.get("documento"), dados.get("lote"),
                dados.get("data_validade"),
            ))
        if rota == "/api/itens/precos":
            try:
                resultado = itens.cadastrar_valor_item(dados.get("item_id"), dados.get("valor"), dados.get("data_inicio_valor"))
            except (TypeError, ValueError) as erro:
                resultado = {"sucesso": False, "erro": "Preço inválido."}
            return self._resultado_operacao(resultado)
        if rota == "/api/colaboradores/editar":
            return self._resultado_operacao(editar_colaborador(dados.get("id"), dados.get("nome"), dados.get("cpf"), dados.get("status")), criado=False)
        if rota == "/api/colaboradores/senha":
            return self._resultado_operacao(redefinir_senha(dados.get("id"), dados.get("senha")), criado=False)
        if rota == "/api/setores":
            resultado = despesas.cadastrar_setor(dados.get("nome"))
            return self._resultado_operacao(resultado)
        if rota == "/api/setores/editar":
            return self._resultado_operacao(
                despesas.editar_setor(dados.get("id"), dados.get("nome"), dados.get("ativo", 1)),
                criado=False,
            )
        if rota == "/api/despesas":
            resultado = despesas.cadastrar_despesa(
                dados.get("setor_id"), dados.get("descricao"),
                dados.get("natureza", "VARIAVEL"), str(dados.get("recorrente", "0")) in ("1", "true", "True"),
            )
            return self._resultado_operacao(resultado)
        if rota == "/api/contas-pagar":
            try:
                resultado = contas_pagar.cadastrar_conta(dados.get("despesa_id"), dados.get("data_vencimento"), _centavos(dados.get("valor")))
            except ValueError as erro:
                resultado = {"sucesso": False, "erro": str(erro)}
            return self._resultado_operacao(resultado)
        if rota == "/api/pagamentos-saida":
            try:
                resultado = pagamentos.registrar_pagamento(dados.get("conta_pagar_id"), dados.get("data_pagamento"), _centavos(dados.get("valor")), dados.get("forma_pagamento"), dados.get("observacao"))
            except ValueError as erro:
                resultado = {"sucesso": False, "erro": str(erro)}
            return self._resultado_operacao(resultado)
        if rota == "/api/recebimentos":
            try:
                resultado = recebimentos.registrar_pagamento(dados.get("cobranca_id"), dados.get("data_pagamento"), _centavos(dados.get("valor")), dados.get("forma_pagamento"), dados.get("observacao"))
            except (TypeError, ValueError) as erro:
                resultado = {"sucesso": False, "erro": str(erro)}
            return self._resultado_operacao(resultado)
        if rota == "/api/cobrancas/desconto":
            try:
                resultado = aplicar_desconto(dados.get("cobranca_id"), _centavos(dados.get("valor")))
            except (TypeError, ValueError) as erro:
                resultado = {"sucesso": False, "erro": str(erro)}
            return self._resultado_operacao(resultado)
        if rota == "/api/contas-pagar/cancelar":
            return self._resultado_operacao(contas_pagar.cancelar_conta(dados.get("conta_id")), criado=False)
        if rota == "/api/pagamentos-saida/excluir":
            return self._resultado_operacao(pagamentos.excluir_pagamento(dados.get("pagamento_id"), dados.get("motivo")), criado=False)
        if rota == "/api/recebimentos/excluir":
            return self._resultado_operacao(recebimentos.excluir_recebimento(dados.get("recebimento_id"), dados.get("motivo")), criado=False)
        if rota == "/api/despesas/desativar":
            return self._resultado_operacao(despesas.desativar_despesa(dados.get("id")), criado=False)
        return self._json({"erro": "Rota não encontrada."}, HTTPStatus.NOT_FOUND)

    def _get_api(self, rota, query):
        inicio = _parametro(query, "data_inicio")
        fim = _parametro(query, "data_fim")
        rotas = {
            "/api/dashboard": _dashboard,
            "/api/residentes": listar_residentes,
            "/api/residentes/extrato": lambda: extrato_residente.consultar(_parametro(query, "id"), inicio, fim),
            "/api/recibos": lambda: recibos.consultar(_parametro(query, "id")),
            "/api/responsaveis": listar_responsaveis,
            "/api/internacoes": listar_internacoes,
            "/api/convenios": lambda: convenios.listar_convenios(False),
            "/api/colaboradores": listar_colaboradores,
            "/api/carteiras": listar_carteiras,
            "/api/carteiras/detalhe": lambda: cantina.consultar_carteira(_parametro(query, "id")),
            "/api/cantina": cantina.consultar_cantina,
            "/api/cantina/produto": lambda: cantina.buscar_produto_codigo(
                _parametro(query, "codigo"), _parametro(query, "data")
            ),
            "/api/itens": lambda: itens.listar_itens(apenas_ativos=False),
            "/api/itens/historico": lambda: {
                "precos": itens.listar_valores_item(_parametro(query, "id"), apenas_ativos=False),
                "estoque": itens.listar_movimentacoes_estoque(_parametro(query, "id")),
            },
            "/api/contas-receber": lambda: contas_receber.listar_cobrancas_consolidadas(data_referencia=date.today().isoformat()),
            "/api/mensalidades": lambda: contas_receber.listar_mensalidades(data_referencia=date.today().isoformat()),
            "/api/contas-pagar": lambda: _listar_contas_pagar(_parametro(query, "status"), inicio, fim),
            "/api/caixa": lambda: {**caixa.resumo_caixa(inicio, fim), "movimentacoes": caixa.listar_movimentacoes(inicio, fim)},
            "/api/despesas": lambda: despesas.listar_despesas(apenas_ativas=False),
            "/api/financeiro/cadastros": lambda: {"setores": despesas.listar_setores(False), "despesas": despesas.listar_despesas(False)},
            "/api/contas-pagar/pagamentos": lambda: historico("pagamentos_saida", _parametro(query, "id"), pagamentos.listar_pagamentos(_parametro(query, "id"))),
            "/api/contas-receber/recebimentos": lambda: historico("recebimentos", _parametro(query, "id"), recebimentos.buscar_pagamentos(_parametro(query, "id"))),
            "/api/cobrancas/ajustes": lambda: historico_ajustes(_parametro(query, "id")),
            "/api/configuracoes": configuracoes_financeiras.obter_configuracao,
            "/api/sincronizacao/status": sincronizacao_nuvem.obter_status,
            "/api/relatorios": lambda: relatorios.gerar(_parametro(query, "tipo", "financeiro"), inicio, fim),
            "/api/auditoria": lambda: auditoria.listar(_parametro(query, "limite", 500)),
        }
        funcao = rotas.get(rota)
        if funcao is None:
            return self._json({"erro": "Rota não encontrada."}, HTTPStatus.NOT_FOUND)
        try:
            return self._json({"dados": funcao()})
        except (TypeError, ValueError) as erro:
            return self._json({"erro": str(erro)}, HTTPStatus.BAD_REQUEST)

    def _resultado_operacao(self, resultado, criado=True):
        status = HTTPStatus.CREATED if criado else HTTPStatus.OK
        return self._json(resultado, status if resultado.get("sucesso") else HTTPStatus.BAD_REQUEST)

    def _arquivo_estatico(self, rota):
        relativo = "index.html" if rota in ("", "/") else rota.lstrip("/")
        arquivo = (RAIZ_FRONTEND / relativo).resolve()
        if RAIZ_FRONTEND.resolve() not in arquivo.parents and arquivo != RAIZ_FRONTEND.resolve():
            return self.send_error(HTTPStatus.FORBIDDEN)
        if not arquivo.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        conteudo = arquivo.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(arquivo.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(conteudo)

    def _corpo_json(self):
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(tamanho) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"erro": "JSON inválido."}, HTTPStatus.BAD_REQUEST)
            return None

    def _token_sessao(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie.get("sessao").value if cookie.get("sessao") else None

    def _sessao(self):
        token = self._token_sessao()
        with LOCK_SESSOES:
            return SESSOES.get(token)

    def _json(self, dados, status=HTTPStatus.OK, cookie=None):
        rota_auditoria = getattr(self, "_rota_auditoria", None)
        if (
            rota_auditoria and not getattr(self, "_auditoria_registrada", False)
            and status < 400 and isinstance(dados, dict) and dados.get("sucesso") is True
            and rota_auditoria not in (
                "/api/auth/login", "/api/auth/logout", "/api/sincronizacao/publicar",
                "/api/sincronizacao/atualizar",
            )
        ):
            self._auditoria_registrada = True
            try:
                auditoria.registrar(
                    "INCLUSAO" if status == HTTPStatus.CREATED else "ALTERACAO",
                    rota_auditoria.removeprefix("/api/"), dados.get("id"),
                    getattr(self, "_dados_auditoria", {}), self._sessao(), self.client_address[0],
                )
            except Exception as erro:
                print(f"Falha ao registrar auditoria: {erro}")
        conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(conteudo)

    def log_message(self, formato, *argumentos):
        print(f"{self.address_string()} - {formato % argumentos}")


def executar(host="127.0.0.1", porta=8000, abrir_navegador=False):
    servidor, endereco, backup = criar_servidor(host, porta)
    print(f"Controle Financeiro disponível em {endereco}")
    print(f"Backup diário verificado: {backup}")
    print("Pressione Ctrl+C para encerrar.")
    if abrir_navegador:
        threading.Timer(0.8, webbrowser.open, args=(endereco,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


def criar_servidor(host="127.0.0.1", porta=8000):
    """Prepara o backend sem iniciar navegador nem bloquear a thread atual."""
    criar_tabelas()
    backup = criar_backup_diario()
    sincronizar_status_residentes()
    endereco = f"http://{host}:{porta}"
    try:
        servidor = ThreadingHTTPServer((host, porta), Requisicao)
    except OSError as erro:
        raise SystemExit(
            f"Não foi possível iniciar o sistema em {endereco}. "
            "Verifique se ele já está aberto em outra janela."
        ) from erro

    return servidor, endereco, backup


if __name__ == "__main__":
    executar()
