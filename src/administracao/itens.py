"""Regras transacionais do inventário administrativo."""
import json
import sqlite3
import unicodedata
from contextlib import closing
from datetime import date

from src.financeiro.api_publica import consultar_setor
from src.financeiro.moeda import validar_centavos
from src.infraestrutura.banco import conectar
from src.nucleo.validacao import inteiro

ESTADOS = {"NOVO", "BOM", "REGULAR", "RUIM", "INSERVIVEL"}
ORDENS = {"nome_asc": "i.nome COLLATE NOCASE,i.id", "nome_desc": "i.nome COLLATE NOCASE DESC,i.id DESC",
          "cadastro_desc": "i.id DESC", "quantidade_desc": "i.quantidade DESC,i.id"}
_MANTER_LOCAL = object()


class ConflitoVersao(ValueError): pass


def _texto(valor, nome, limite, obrigatorio=False, maiusculo=False):
    if valor is None: texto = ""
    elif not isinstance(valor, str): raise ValueError(f"{nome} deve ser um texto.")
    else: texto = valor.strip()
    if obrigatorio and not texto: raise ValueError(f"Informe {nome.lower()}.")
    if len(texto) > limite: raise ValueError(f"{nome} deve ter até {limite} caracteres.")
    return (texto.upper() if maiusculo else texto) or None


def _data(valor, nome, obrigatoria=False):
    if valor in (None, ""):
        if obrigatoria: raise ValueError(f"Informe {nome.lower()}.")
        return None
    try:
        if not isinstance(valor, str) or date.fromisoformat(valor).isoformat() != valor: raise ValueError
    except ValueError: raise ValueError(f"{nome} deve ser uma data válida no formato AAAA-MM-DD.") from None
    if valor > date.today().isoformat(): raise ValueError(f"{nome} não pode ser futura.")
    return valor


def _inteiro(valor, nome, minimo=0): return inteiro(valor, nome, minimo)


def _setor(conn, identificador, ativo=False):
    setor = consultar_setor(_inteiro(identificador, "setor_id", 1), conn)
    if not setor: raise ValueError("Setor não encontrado.")
    if ativo and not setor["ativo"]: raise ValueError("O setor deve estar ativo para esta operação.")
    return setor


def _item(conn, item_id):
    conn.row_factory = sqlite3.Row
    linha = conn.execute("SELECT i.*,s.nome setor_nome,s.ativo setor_ativo FROM itens_administracao i JOIN setores s ON s.id=i.setor_id WHERE i.id=?", (_inteiro(item_id,"id",1),)).fetchone()
    if not linha: raise ValueError("Item administrativo não encontrado.")
    return dict(linha)


def _versao(item, esperada):
    esperada = _inteiro(esperada, "versao_esperada", 1)
    if item["versao"] != esperada: raise ConflitoVersao("O item foi alterado por outra operação. Recarregue os dados antes de continuar.")


def _snap(item):
    campos = ("nome","descricao","categoria","codigo_patrimonio","unidade_medida","data_aquisicao","valor_aquisicao","estado_conservacao","ativo")
    return json.dumps({k:item.get(k) for k in campos}, ensure_ascii=False, sort_keys=True)


def _evento(conn, item, tipo, data_mov, anterior, resultante, motivo, documento=None, setor_novo=None,
            local_nova=_MANTER_LOCAL, dados_anteriores=None, dados_novos=None, versao_resultante=None):
    motivo = _texto(motivo, "Motivo", 2000, True); documento = _texto(documento,"Documento",200)
    data_mov = _data(data_mov, "Data da movimentação", True)
    if item.get("data_aquisicao") and data_mov < item["data_aquisicao"]:
        raise ValueError("A movimentação não pode ser anterior à aquisição.")
    novo = setor_novo or {"id":item["setor_id"], "nome":item["setor_nome"]}
    vr = versao_resultante or item["versao"] + 1
    conn.execute("""INSERT INTO movimentacoes_itens_administracao
      (item_id,tipo,data_movimentacao,quantidade_anterior,quantidade_movimentada,variacao,quantidade_resultante,
       setor_anterior_id,setor_anterior_nome,setor_novo_id,setor_novo_nome,localizacao_anterior,localizacao_nova,
       motivo,documento,versao_anterior,versao_resultante,dados_anteriores,dados_novos)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      (item["id"],tipo,data_mov,anterior,abs(resultante-anterior),resultante-anterior,resultante,
       item["setor_id"],item["setor_nome"],novo["id"],novo["nome"],item.get("localizacao"),
       item.get("localizacao") if local_nova is _MANTER_LOCAL else local_nova,motivo,documento,item["versao"],vr,
       dados_anteriores,dados_novos))


def cadastrar(nome, descricao, categoria, codigo_patrimonio, quantidade_inicial, unidade_medida, setor_id,
              data_aquisicao, valor_aquisicao, estado_conservacao, localizacao, data_movimentacao, motivo, documento=None):
    nome=_texto(nome,"Nome",200,True); descricao=_texto(descricao,"Descrição",2000); categoria=_texto(categoria,"Categoria",100)
    patrimonio=_texto(codigo_patrimonio,"Código patrimonial",100,maiusculo=True)
    quantidade=_inteiro(quantidade_inicial,"quantidade_inicial",1)
    if patrimonio and quantidade != 1: raise ValueError("Item com patrimônio deve representar exatamente uma unidade.")
    unidade=_texto(unidade_medida or "UN","Unidade de medida",20,True,True)
    aquisicao=_data(data_aquisicao,"Data de aquisição")
    movimento=_data(data_movimentacao or date.today().isoformat(),"Data de entrada",True)
    if aquisicao and movimento < aquisicao: raise ValueError("A entrada não pode ser anterior à aquisição.")
    if valor_aquisicao is not None: valor_aquisicao=validar_centavos(valor_aquisicao)
    if valor_aquisicao is not None and valor_aquisicao < 0: raise ValueError("Valor de aquisição não pode ser negativo.")
    estado=str(estado_conservacao or "").upper()
    if estado not in ESTADOS: raise ValueError("Estado de conservação inválido.")
    localizacao=_texto(localizacao,"Localização",200)
    with closing(conectar()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE"); setor=_setor(conn,setor_id,True)
        try:
            cur=conn.execute("""INSERT INTO itens_administracao
              (nome,descricao,categoria,codigo_patrimonio,quantidade,unidade_medida,setor_id,data_aquisicao,
               valor_aquisicao,estado_conservacao,localizacao) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
              (nome,descricao,categoria,patrimonio,quantidade,unidade,setor["id"],aquisicao,valor_aquisicao,estado,localizacao))
        except sqlite3.IntegrityError as erro:
            if "codigo_patrimonio" in str(erro): raise ValueError("Código patrimonial já cadastrado.") from erro
            raise
        item=_item(conn,cur.lastrowid); item["versao"]=0
        _evento(conn,item,"CADASTRO",movimento,0,quantidade,motivo,documento,setor,localizacao,None,_snap({**item,"versao":1}),1)
        return {"sucesso":True,"id":cur.lastrowid,"versao":1}


def detalhe(item_id):
    with closing(conectar()) as conn: return _item(conn,item_id)


def listar(busca=None,setor_id=None,categoria=None,estado_conservacao=None,ativo=None,pagina=1,tamanho=50,ordem="nome_asc"):
    pagina=_inteiro(pagina,"pagina",1); tamanho=min(_inteiro(tamanho,"tamanho",1),200)
    if ordem not in ORDENS: raise ValueError("Ordenação inválida.")
    filtros=[]; params=[]
    if busca:
        termo="%"+unicodedata.normalize("NFKD",str(busca)).encode("ascii","ignore").decode().lower()+"%"
        filtros.append("normalizar(i.nome||' '||COALESCE(i.descricao,'')||' '||COALESCE(i.codigo_patrimonio,'')||' '||COALESCE(i.localizacao,'')) LIKE ?"); params.append(termo)
    if setor_id not in (None,""): filtros.append("i.setor_id=?"); params.append(_inteiro(setor_id,"setor_id",1))
    if categoria not in (None,""): filtros.append("i.categoria=?"); params.append(str(categoria))
    if estado_conservacao not in (None,""):
        estado=str(estado_conservacao).upper()
        if estado not in ESTADOS: raise ValueError("Estado de conservação inválido.")
        filtros.append("i.estado_conservacao=?"); params.append(estado)
    if ativo not in (None,""):
        if isinstance(ativo,bool) or str(ativo) not in ("0","1"): raise ValueError("Situação inválida.")
        filtros.append("i.ativo=?"); params.append(int(ativo))
    where=" WHERE "+" AND ".join(filtros) if filtros else ""
    with closing(conectar()) as conn:
        conn.row_factory=sqlite3.Row
        conn.create_function("normalizar",1,lambda x: unicodedata.normalize("NFKD",str(x or "")).encode("ascii","ignore").decode().lower())
        base=" FROM itens_administracao i JOIN setores s ON s.id=i.setor_id"
        total=conn.execute("SELECT COUNT(*) FROM itens_administracao").fetchone()[0]
        filtrado=conn.execute("SELECT COUNT(*)"+base+where,params).fetchone()[0]
        linhas=[dict(r) for r in conn.execute("SELECT i.*,s.nome setor_nome,s.ativo setor_ativo"+base+where+f" ORDER BY {ORDENS[ordem]} LIMIT ? OFFSET ?",(*params,tamanho,(pagina-1)*tamanho))]
        indicadores={"registros":filtrado,"ativos":0,"ruim":0,"inservivel":0,"quantidades":{}}
        for r in conn.execute("SELECT i.ativo,i.estado_conservacao,i.unidade_medida,SUM(i.quantidade) quantidade"+base+where+" GROUP BY i.ativo,i.estado_conservacao,i.unidade_medida",params):
            indicadores["quantidades"][r[2]]=indicadores["quantidades"].get(r[2],0)+r[3]
        indicadores["ativos"]=conn.execute("SELECT COUNT(*)"+base+where+(" AND" if where else " WHERE")+" i.ativo=1",params).fetchone()[0]
        indicadores["ruim"]=conn.execute("SELECT COUNT(*)"+base+where+(" AND" if where else " WHERE")+" i.estado_conservacao='RUIM'",params).fetchone()[0]
        indicadores["inservivel"]=conn.execute("SELECT COUNT(*)"+base+where+(" AND" if where else " WHERE")+" i.estado_conservacao='INSERVIVEL'",params).fetchone()[0]
        return {"linhas":linhas,"pagina":pagina,"tamanho":tamanho,"total_geral":total,"total_filtrado":filtrado,"indicadores":indicadores}


def editar(item_id,versao_esperada,nome,descricao,categoria,codigo_patrimonio,data_aquisicao,
           valor_aquisicao,estado_conservacao,motivo):
    nome=_texto(nome,"Nome",200,True); descricao=_texto(descricao,"Descrição",2000); categoria=_texto(categoria,"Categoria",100)
    patrimonio=_texto(codigo_patrimonio,"Código patrimonial",100,maiusculo=True); aquisicao=_data(data_aquisicao,"Data de aquisição")
    if valor_aquisicao is not None: valor_aquisicao=validar_centavos(valor_aquisicao)
    if valor_aquisicao is not None and valor_aquisicao<0: raise ValueError("Valor de aquisição não pode ser negativo.")
    estado=str(estado_conservacao or "").upper()
    if estado not in ESTADOS: raise ValueError("Estado de conservação inválido.")
    motivo=_texto(motivo,"Motivo",2000,True)
    with closing(conectar()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE"); item=_item(conn,item_id); _versao(item,versao_esperada)
        if item["codigo_patrimonio"] and not patrimonio: raise ValueError("Não é permitido remover um código patrimonial existente.")
        if patrimonio and item["quantidade"]>1: raise ValueError("Patrimônio individual não pode possuir mais de uma unidade.")
        if aquisicao:
            primeira=conn.execute("SELECT MIN(data_movimentacao) FROM movimentacoes_itens_administracao WHERE item_id=?",(item["id"],)).fetchone()[0]
            if primeira and aquisicao>primeira: raise ValueError("A aquisição não pode ser posterior a uma movimentação registrada.")
        novos={**item,"nome":nome,"descricao":descricao,"categoria":categoria,"codigo_patrimonio":patrimonio,
               "data_aquisicao":aquisicao,"valor_aquisicao":valor_aquisicao,"estado_conservacao":estado}
        if _snap(item)==_snap(novos): raise ValueError("Nenhuma alteração cadastral foi informada.")
        try:
            cur=conn.execute("""UPDATE itens_administracao SET nome=?,descricao=?,categoria=?,codigo_patrimonio=?,data_aquisicao=?,
              valor_aquisicao=?,estado_conservacao=?,versao=versao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND versao=?""",
              (nome,descricao,categoria,patrimonio,aquisicao,valor_aquisicao,estado,item["id"],item["versao"]))
        except sqlite3.IntegrityError as erro: raise ValueError("Código patrimonial já cadastrado.") from erro
        if cur.rowcount!=1: raise ConflitoVersao("O item foi alterado por outra operação.")
        _evento(conn,item,"EDICAO",date.today().isoformat(),item["quantidade"],item["quantidade"],motivo,
                dados_anteriores=_snap(item),dados_novos=_snap(novos))
        return {"sucesso":True,"id":item["id"],"versao":item["versao"]+1}


def movimentar(item_id,versao_esperada,tipo,data_movimentacao,motivo,documento=None,quantidade=None,quantidade_alvo=None):
    tipo=str(tipo or "").upper()
    if tipo not in {"ENTRADA","SAIDA","AJUSTE","BAIXA"}: raise ValueError("Tipo de movimentação inválido.")
    if tipo=="AJUSTE":
        if quantidade not in (None,"") or quantidade_alvo in (None,""): raise ValueError("Ajuste deve informar somente a quantidade alvo.")
        alvo=_inteiro(quantidade_alvo,"quantidade_alvo",0)
    else:
        if quantidade_alvo not in (None,"") or quantidade in (None,""): raise ValueError("Informe somente a quantidade da movimentação.")
        mov=_inteiro(quantidade,"quantidade",1)
    with closing(conectar()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE"); item=_item(conn,item_id); _versao(item,versao_esperada)
        if not item["ativo"]: raise ValueError("Reative o item antes de movimentá-lo.")
        if tipo=="ENTRADA": result=item["quantidade"]+mov
        elif tipo in {"SAIDA","BAIXA"}: result=item["quantidade"]-mov
        else: result=alvo
        if result<0: raise ValueError("Saldo insuficiente para a movimentação.")
        if item["codigo_patrimonio"] and result>1: raise ValueError("Patrimônio individual aceita saldo máximo de uma unidade.")
        if tipo=="AJUSTE" and result==item["quantidade"]: raise ValueError("O ajuste não altera o saldo atual.")
        aumenta=result>item["quantidade"]
        if aumenta and not item["setor_ativo"]: raise ValueError("Setor inativo não permite aumento de saldo.")
        ativo_novo=0 if tipo=="BAIXA" and result==0 else item["ativo"]
        cur=conn.execute("UPDATE itens_administracao SET quantidade=?,ativo=?,versao=versao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND versao=?",
                         (result,ativo_novo,item["id"],item["versao"]))
        if cur.rowcount!=1: raise ConflitoVersao("O item foi alterado por outra operação.")
        novos={**item,"ativo":ativo_novo}
        _evento(conn,item,tipo,data_movimentacao,item["quantidade"],result,motivo,documento,
                dados_anteriores=_snap(item) if ativo_novo!=item["ativo"] else None,
                dados_novos=_snap(novos) if ativo_novo!=item["ativo"] else None)
        return {"sucesso":True,"id":item["id"],"versao":item["versao"]+1,"quantidade":result,"ativo":ativo_novo}


def transferir(item_id,versao_esperada,setor_destino_id,localizacao_destino,data_movimentacao,motivo):
    local=_texto(localizacao_destino,"Localização de destino",200)
    with closing(conectar()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE"); item=_item(conn,item_id); _versao(item,versao_esperada)
        if not item["ativo"]: raise ValueError("Reative o item antes de transferi-lo.")
        if item["quantidade"]<=0: raise ValueError("Somente itens com saldo positivo podem ser transferidos.")
        destino=_setor(conn,setor_destino_id,True)
        if destino["id"]==item["setor_id"] and local==item["localizacao"]: raise ValueError("O destino é igual ao setor e localização atuais.")
        cur=conn.execute("UPDATE itens_administracao SET setor_id=?,localizacao=?,versao=versao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND versao=?",
                         (destino["id"],local,item["id"],item["versao"]))
        if cur.rowcount!=1: raise ConflitoVersao("O item foi alterado por outra operação.")
        _evento(conn,item,"TRANSFERENCIA",data_movimentacao,item["quantidade"],item["quantidade"],motivo,
                setor_novo=destino,local_nova=local)
        return {"sucesso":True,"id":item["id"],"versao":item["versao"]+1}


def alterar_status(item_id,versao_esperada,ativo,motivo):
    if isinstance(ativo,bool): novo=int(ativo)
    elif str(ativo) in ("0","1"): novo=int(ativo)
    else: raise ValueError("Situação inválida.")
    with closing(conectar()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE"); item=_item(conn,item_id); _versao(item,versao_esperada)
        if novo==item["ativo"]: raise ValueError("O item já possui esta situação.")
        if not novo and item["quantidade"]!=0: raise ValueError("A inativação manual exige saldo zero.")
        if novo: _setor(conn,item["setor_id"],True)
        cur=conn.execute("UPDATE itens_administracao SET ativo=?,versao=versao+1,atualizado_em=CURRENT_TIMESTAMP WHERE id=? AND versao=?",
                         (novo,item["id"],item["versao"]))
        if cur.rowcount!=1: raise ConflitoVersao("O item foi alterado por outra operação.")
        novos={**item,"ativo":novo}
        _evento(conn,item,"REATIVACAO" if novo else "INATIVACAO",date.today().isoformat(),item["quantidade"],item["quantidade"],motivo,
                dados_anteriores=_snap(item),dados_novos=_snap(novos))
        return {"sucesso":True,"id":item["id"],"versao":item["versao"]+1,"ativo":novo}


def historico(item_id,pagina=1,tamanho=50):
    item_id=_inteiro(item_id,"id",1); pagina=_inteiro(pagina,"pagina",1); tamanho=min(_inteiro(tamanho,"tamanho",1),200)
    with closing(conectar()) as conn:
        conn.row_factory=sqlite3.Row
        if not conn.execute("SELECT 1 FROM itens_administracao WHERE id=?",(item_id,)).fetchone(): raise ValueError("Item administrativo não encontrado.")
        total=conn.execute("SELECT COUNT(*) FROM movimentacoes_itens_administracao WHERE item_id=?",(item_id,)).fetchone()[0]
        linhas=[dict(r) for r in conn.execute("SELECT * FROM movimentacoes_itens_administracao WHERE item_id=? ORDER BY id LIMIT ? OFFSET ?",(item_id,tamanho,(pagina-1)*tamanho))]
        return {"linhas":linhas,"pagina":pagina,"tamanho":tamanho,"total":total}
