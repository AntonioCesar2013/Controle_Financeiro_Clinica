from src.nucleo.migracoes import Migracao, aplicar_migracoes
from src.nucleo.modulos import Modulo


def _schema(conexao):
    conexao.execute("""CREATE TABLE itens_administracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL CHECK(typeof(nome)='text' AND length(trim(nome)) BETWEEN 1 AND 200),
        descricao TEXT CHECK(descricao IS NULL OR length(descricao)<=2000),
        categoria TEXT CHECK(categoria IS NULL OR length(categoria)<=100),
        codigo_patrimonio TEXT UNIQUE CHECK(codigo_patrimonio IS NULL OR (length(codigo_patrimonio) BETWEEN 1 AND 100 AND codigo_patrimonio=upper(trim(codigo_patrimonio)))),
        quantidade INTEGER NOT NULL CHECK(typeof(quantidade)='integer' AND quantidade>=0 AND (codigo_patrimonio IS NULL OR quantidade<=1)),
        unidade_medida TEXT NOT NULL DEFAULT 'UN' CHECK(typeof(unidade_medida)='text' AND length(trim(unidade_medida)) BETWEEN 1 AND 20),
        setor_id INTEGER NOT NULL REFERENCES setores(id) ON DELETE RESTRICT,
        data_aquisicao TEXT,
        valor_aquisicao INTEGER CHECK(valor_aquisicao IS NULL OR (typeof(valor_aquisicao)='integer' AND valor_aquisicao BETWEEN 0 AND 9000000000000000)),
        estado_conservacao TEXT NOT NULL CHECK(estado_conservacao IN ('NOVO','BOM','REGULAR','RUIM','INSERVIVEL')),
        localizacao TEXT CHECK(localizacao IS NULL OR length(localizacao)<=200),
        ativo INTEGER NOT NULL DEFAULT 1 CHECK(typeof(ativo)='integer' AND ativo IN (0,1)),
        versao INTEGER NOT NULL DEFAULT 1 CHECK(typeof(versao)='integer' AND versao>=1),
        cadastrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conexao.execute("CREATE INDEX idx_itens_administracao_setor_ativo ON itens_administracao(setor_id,ativo,id)")
    conexao.execute("CREATE INDEX idx_itens_administracao_nome ON itens_administracao(nome,id)")
    conexao.execute("""CREATE TABLE movimentacoes_itens_administracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL REFERENCES itens_administracao(id) ON DELETE RESTRICT,
        tipo TEXT NOT NULL CHECK(tipo IN ('CADASTRO','ENTRADA','SAIDA','AJUSTE','TRANSFERENCIA','BAIXA','EDICAO','INATIVACAO','REATIVACAO')),
        data_movimentacao TEXT NOT NULL,
        registrado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        quantidade_anterior INTEGER NOT NULL CHECK(quantidade_anterior>=0),
        quantidade_movimentada INTEGER NOT NULL CHECK(quantidade_movimentada>=0),
        variacao INTEGER NOT NULL,
        quantidade_resultante INTEGER NOT NULL CHECK(quantidade_resultante>=0 AND quantidade_resultante=quantidade_anterior+variacao AND quantidade_movimentada=abs(variacao)),
        setor_anterior_id INTEGER REFERENCES setores(id) ON DELETE RESTRICT,
        setor_anterior_nome TEXT,
        setor_novo_id INTEGER REFERENCES setores(id) ON DELETE RESTRICT,
        setor_novo_nome TEXT,
        localizacao_anterior TEXT, localizacao_nova TEXT,
        motivo TEXT NOT NULL CHECK(length(trim(motivo)) BETWEEN 1 AND 2000),
        documento TEXT CHECK(documento IS NULL OR length(documento)<=200),
        versao_anterior INTEGER NOT NULL, versao_resultante INTEGER NOT NULL,
        dados_anteriores TEXT, dados_novos TEXT
    )""")
    conexao.execute("CREATE INDEX idx_mov_itens_administracao_item ON movimentacoes_itens_administracao(item_id,id)")


def preparar_banco(conexao):
    aplicar_migracoes(conexao, (Migracao("administracao", 1, _schema),))


MODULO = Modulo("administracao", preparar_banco)
