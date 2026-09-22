"""
Arquivo: models.py
Propósito:
    Definir o esquema SQL completo do sistema de inventário de celulares.
    O projeto mantém scripts separados para SQLite e PostgreSQL.
"""

SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS aparelhos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linha TEXT,
    estab TEXT,
    mdm_id INTEGER,
    tipo_linha TEXT,
    status TEXT,
    uso TEXT,
    usuario TEXT,
    nivel TEXT,
    nr_cartao INTEGER,
    responsavel TEXT,
    cargo TEXT,
    situacao TEXT,
    centro_custo TEXT,
    departamento TEXT,
    internet TEXT,
    grupo TEXT,
    marca TEXT,
    modelo_mdm TEXT,
    modelo TEXT,
    imei_mdm TEXT,
    imei TEXT,
    chip TEXT,
    mac_wifi TEXT,
    serial TEXT,
    conta_google TEXT,
    observacoes TEXT,
    data_desligamento DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linha TEXT,
    chip TEXT,
    status TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS estoque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidade TEXT,
    marca TEXT,
    modelo TEXT,
    imei TEXT,
    centro_custo TEXT,
    observacoes TEXT,
    status TEXT DEFAULT 'DISPONÍVEL'
);

CREATE TABLE IF NOT EXISTS devolvidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo TEXT,
    imei TEXT,
    antigo_usuario TEXT,
    unidade TEXT,
    observacao TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS descarte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo TEXT,
    imei TEXT,
    antigo_usuario TEXT,
    unidade TEXT,
    observacao TEXT,
    status TEXT,
    data_descarte DATE
);

CREATE TABLE IF NOT EXISTS colaboradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula TEXT,
    nome TEXT,
    estabelecimento TEXT,
    cargo TEXT,
    centro_custo TEXT,
    departamento TEXT,
    data_admissao DATE,
    data_desligamento DATE
);

CREATE TABLE IF NOT EXISTS grupos_whatsapp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grupo TEXT,
    linha TEXT,
    nome_integrante TEXT,
    administrador BOOLEAN,
    unidade TEXT,
    linha_corporativa BOOLEAN,
    responsavel_informar TEXT
);

CREATE TABLE IF NOT EXISTS centros_custo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT,
    titulo TEXT
);

CREATE TABLE IF NOT EXISTS estabelecimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tipos_linha (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS status_aparelho (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS usos_aparelho (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS niveis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS empresas_suporte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS historico_chips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chip TEXT NOT NULL,
    aparelho_id INTEGER,
    imei TEXT,
    linha TEXT,
    data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT,
    FOREIGN KEY (aparelho_id) REFERENCES aparelhos(id)
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entidade TEXT NOT NULL,
    entidade_id INTEGER,
    acao TEXT NOT NULL,
    descricao TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manutencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo INTEGER UNIQUE NOT NULL,
    aparelho_id INTEGER NOT NULL,
    id_pulsus INTEGER,
    imei TEXT,
    marca TEXT,
    modelo TEXT,
    problema_reportado TEXT,
    usuario TEXT,
    centro_custo TEXT,
    aprovador TEXT,
    estab TEXT,
    unidade TEXT,
    empresa_suporte TEXT,
    data_envio DATE,
    nf_envio TEXT,
    descricao_manutencao TEXT,
    orcamento DECIMAL(10,2),
    valor_final DECIMAL(10,2),
    numero_pedido TEXT,
    status TEXT NOT NULL CHECK (status IN ('ENVIAR PARA MANUTENÇÃO', 'AGUARDANDO ORÇAMENTO', 'AGUARDANDO APROVAÇÃO', 'APROVADO', 'RECUSADO', 'GARANTIA')),
    data_retorno DATE,
    numero_chamado TEXT,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (aparelho_id) REFERENCES aparelhos(id)
);

-- Log de importacoes
CREATE TABLE IF NOT EXISTS log_importacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL,
    nome_arquivo TEXT NOT NULL,
    total_linhas INTEGER NOT NULL,
    inseridas INTEGER DEFAULT 0,
    atualizadas INTEGER DEFAULT 0,
    ignoradas INTEGER DEFAULT 0,
    detalhes_erros TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aparelhos_linha ON aparelhos(linha);
CREATE INDEX IF NOT EXISTS idx_aparelhos_imei ON aparelhos(imei);
CREATE INDEX IF NOT EXISTS idx_aparelhos_usuario ON aparelhos(usuario);
CREATE INDEX IF NOT EXISTS idx_chips_chip ON chips(chip);
CREATE INDEX IF NOT EXISTS idx_colaboradores_nome ON colaboradores(nome);
CREATE INDEX IF NOT EXISTS idx_manutencoes_aparelho_id ON manutencoes(aparelho_id);
CREATE INDEX IF NOT EXISTS idx_manutencoes_status ON manutencoes(status);
CREATE INDEX IF NOT EXISTS idx_manutencoes_codigo ON manutencoes(codigo);
CREATE INDEX IF NOT EXISTS idx_manutencoes_data_envio ON manutencoes(data_envio);

CREATE TRIGGER IF NOT EXISTS trg_aparelhos_updated_at
AFTER UPDATE ON aparelhos
FOR EACH ROW
BEGIN
    UPDATE aparelhos
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_manutencoes_updated_at
AFTER UPDATE ON manutencoes
FOR EACH ROW
BEGIN
    UPDATE manutencoes
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;
"""

POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS aparelhos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    linha TEXT,
    estab TEXT,
    mdm_id INTEGER,
    tipo_linha TEXT,
    status TEXT,
    uso TEXT,
    usuario TEXT,
    nivel TEXT,
    nr_cartao INTEGER,
    responsavel TEXT,
    cargo TEXT,
    situacao TEXT,
    centro_custo TEXT,
    departamento TEXT,
    internet TEXT,
    grupo TEXT,
    marca TEXT,
    modelo_mdm TEXT,
    modelo TEXT,
    imei_mdm TEXT,
    imei TEXT,
    chip TEXT,
    mac_wifi TEXT,
    serial TEXT,
    conta_google TEXT,
    observacoes TEXT,
    data_desligamento DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chips (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    linha TEXT,
    chip TEXT,
    status TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS estoque (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unidade TEXT,
    marca TEXT,
    modelo TEXT,
    imei TEXT,
    centro_custo TEXT,
    observacoes TEXT,
    status TEXT DEFAULT 'DISPONÍVEL'
);

CREATE TABLE IF NOT EXISTS devolvidos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    modelo TEXT,
    imei TEXT,
    antigo_usuario TEXT,
    unidade TEXT,
    observacao TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS descarte (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    modelo TEXT,
    imei TEXT,
    antigo_usuario TEXT,
    unidade TEXT,
    observacao TEXT,
    status TEXT,
    data_descarte DATE
);

CREATE TABLE IF NOT EXISTS colaboradores (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    matricula TEXT,
    nome TEXT,
    estabelecimento TEXT,
    cargo TEXT,
    centro_custo TEXT,
    departamento TEXT,
    data_admissao DATE,
    data_desligamento DATE
);

CREATE TABLE IF NOT EXISTS grupos_whatsapp (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grupo TEXT,
    linha TEXT,
    nome_integrante TEXT,
    administrador BOOLEAN,
    unidade TEXT,
    linha_corporativa BOOLEAN,
    responsavel_informar TEXT
);

CREATE TABLE IF NOT EXISTS centros_custo (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo TEXT,
    titulo TEXT
);

CREATE TABLE IF NOT EXISTS estabelecimentos (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tipos_linha (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS status_aparelho (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS usos_aparelho (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS niveis (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    descricao TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS empresas_suporte (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS historico_chips (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chip TEXT NOT NULL,
    aparelho_id INTEGER,
    imei TEXT,
    linha TEXT,
    data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT,
    FOREIGN KEY (aparelho_id) REFERENCES aparelhos(id)
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entidade TEXT NOT NULL,
    entidade_id INTEGER,
    acao TEXT NOT NULL,
    descricao TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manutencoes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo INTEGER UNIQUE NOT NULL,
    aparelho_id INTEGER NOT NULL,
    id_pulsus INTEGER,
    imei TEXT,
    marca TEXT,
    modelo TEXT,
    problema_reportado TEXT,
    usuario TEXT,
    centro_custo TEXT,
    aprovador TEXT,
    estab TEXT,
    unidade TEXT,
    empresa_suporte TEXT,
    data_envio DATE,
    nf_envio TEXT,
    descricao_manutencao TEXT,
    orcamento DECIMAL(10,2),
    valor_final DECIMAL(10,2),
    numero_pedido TEXT,
    status TEXT NOT NULL CHECK (status IN ('ENVIAR PARA MANUTENÇÃO', 'AGUARDANDO ORÇAMENTO', 'AGUARDANDO APROVAÇÃO', 'APROVADO', 'RECUSADO', 'GARANTIA')),
    data_retorno DATE,
    numero_chamado TEXT,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (aparelho_id) REFERENCES aparelhos(id)
);

-- Log de importacoes
CREATE TABLE IF NOT EXISTS log_importacao (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario TEXT NOT NULL,
    nome_arquivo TEXT NOT NULL,
    total_linhas INTEGER NOT NULL,
    inseridas INTEGER DEFAULT 0,
    atualizadas INTEGER DEFAULT 0,
    ignoradas INTEGER DEFAULT 0,
    detalhes_erros TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aparelhos_linha ON aparelhos(linha);
CREATE INDEX IF NOT EXISTS idx_aparelhos_imei ON aparelhos(imei);
CREATE INDEX IF NOT EXISTS idx_aparelhos_usuario ON aparelhos(usuario);
CREATE INDEX IF NOT EXISTS idx_chips_chip ON chips(chip);
CREATE INDEX IF NOT EXISTS idx_colaboradores_nome ON colaboradores(nome);
CREATE INDEX IF NOT EXISTS idx_manutencoes_aparelho_id ON manutencoes(aparelho_id);
CREATE INDEX IF NOT EXISTS idx_manutencoes_status ON manutencoes(status);
CREATE INDEX IF NOT EXISTS idx_manutencoes_codigo ON manutencoes(codigo);
CREATE INDEX IF NOT EXISTS idx_manutencoes_data_envio ON manutencoes(data_envio);

CREATE OR REPLACE FUNCTION update_aparelhos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_aparelhos_updated_at ON aparelhos;

CREATE TRIGGER trg_aparelhos_updated_at
BEFORE UPDATE ON aparelhos
FOR EACH ROW
EXECUTE FUNCTION update_aparelhos_updated_at();

CREATE OR REPLACE FUNCTION update_manutencoes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_manutencoes_updated_at ON manutencoes;

CREATE TRIGGER trg_manutencoes_updated_at
BEFORE UPDATE ON manutencoes
FOR EACH ROW
EXECUTE FUNCTION update_manutencoes_updated_at();
"""


def get_schema_sql(engine="sqlite"):
    """
    Retorna o script SQL do esquema conforme o banco configurado.

    Parâmetros:
        engine (str): `sqlite` ou `postgres`.

    Retorno:
        str: script SQL completo.
    """
    if engine == "postgres":
        return POSTGRES_SCHEMA_SQL
    return SQLITE_SCHEMA_SQL


def get_postgres_trigger_sql():
    """
    Retorna o SQL de trigger específico do PostgreSQL para atualizar `updated_at`.

    Parâmetros:
        Nenhum.

    Retorno:
        str: SQL da função e da trigger.
    """
    return """
CREATE OR REPLACE FUNCTION update_aparelhos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_aparelhos_updated_at ON aparelhos;

CREATE TRIGGER trg_aparelhos_updated_at
BEFORE UPDATE ON aparelhos
FOR EACH ROW
EXECUTE FUNCTION update_aparelhos_updated_at();
"""