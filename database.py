"""
Arquivo: database.py
Propósito:
    Centralizar a conexão com o banco SQLite ou PostgreSQL e oferecer funções
    utilitárias simples para consultas, escrita e inicialização do esquema.
"""

import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from flask import current_app, g

from models import get_postgres_trigger_sql, get_schema_sql

SQLITE_APARELHOS_OPTIONAL_COLUMNS = {
    "internet": "TEXT",
    "grupo": "TEXT",
    "modelo_mdm": "TEXT",
    "imei_mdm": "TEXT",
    "conta_google": "TEXT",
}


def get_db_engine():
    """
    Identifica o banco ativo a partir da configuração da aplicação.

    Parâmetros:
        Nenhum.

    Retorno:
        str: `postgres` quando DATABASE_URL aponta para PostgreSQL, senão `sqlite`.
    """
    database_url = current_app.config.get("DATABASE_URL", "")
    if database_url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    return "sqlite"


def normalize_database_url(database_url):
    """
    Ajusta a URL do PostgreSQL para o formato aceito pelo driver psycopg.

    Parâmetros:
        database_url (str): URL recebida por variável de ambiente.

    Retorno:
        str: URL pronta para abrir a conexão.
    """
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://") :]
    return database_url


def convert_sql_placeholders(sql):
    """
    Converte os placeholders SQL para o formato esperado pelo banco atual.

    Parâmetros:
        sql (str): instrução SQL escrita com placeholders `?`.

    Retorno:
        str: instrução SQL compatível com o driver em uso.
    """
    if get_db_engine() == "postgres":
        return sql.replace("?", "%s")
    return sql


def get_db():
    """
    Obtém a conexão do banco da requisição atual.

    Parâmetros:
        Nenhum.

    Retorno:
        sqlite3.Connection | psycopg.Connection: conexão aberta e configurada.
    """
    if "db" not in g:
        engine = get_db_engine()

        # g é um espaço temporário do Flask para guardar objetos válidos
        # apenas durante a requisição atual, evitando abrir várias conexões.
        if engine == "postgres":
            database_url = normalize_database_url(current_app.config["DATABASE_URL"])
            g.db = psycopg.connect(database_url, row_factory=dict_row)
        else:
            database_path = Path(current_app.root_path) / current_app.config["DATABASE"]
            g.db = sqlite3.connect(database_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(_error=None):
    """
    Fecha a conexão armazenada no contexto da requisição.

    Parâmetros:
        _error (Exception | None): erro opcional recebido pelo Flask no teardown.

    Retorno:
        None.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, params=()):
    """
    Executa uma consulta e retorna todos os registros.

    Parâmetros:
        sql (str): instrução SQL.
        params (tuple): parâmetros posicionais da consulta.

    Retorno:
        list: lista de linhas encontradas.
    """
    cursor = get_db().execute(convert_sql_placeholders(sql), params)
    rows = cursor.fetchall()
    if hasattr(cursor, "close"):
        cursor.close()
    if rows and isinstance(rows[0], sqlite3.Row):
        return [dict(row) for row in rows]
    return rows


def query_one(sql, params=()):
    """
    Executa uma consulta e retorna apenas um registro.

    Parâmetros:
        sql (str): instrução SQL.
        params (tuple): parâmetros posicionais da consulta.

    Retorno:
        sqlite3.Row | dict | None: linha encontrada ou None.
    """
    cursor = get_db().execute(convert_sql_placeholders(sql), params)
    row = cursor.fetchone()
    if hasattr(cursor, "close"):
        cursor.close()
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return row


def execute(sql, params=()):
    """
    Executa um comando de escrita no banco.

    Parâmetros:
        sql (str): instrução SQL.
        params (tuple): parâmetros posicionais do comando.

    Retorno:
        int | None: id da última linha inserida quando aplicável.
    """
    db = get_db()
    converted_sql = convert_sql_placeholders(sql)
    is_insert = converted_sql.lstrip().upper().startswith("INSERT INTO")

    # No PostgreSQL precisamos pedir explicitamente o id retornado.
    if get_db_engine() == "postgres" and is_insert and "RETURNING" not in converted_sql.upper():
        converted_sql = converted_sql.rstrip().rstrip(";") + " RETURNING id"

    try:
        cursor = db.execute(converted_sql, params)
        lastrowid = None

        if is_insert:
            if get_db_engine() == "postgres":
                inserted_row = cursor.fetchone()
                if inserted_row:
                    lastrowid = inserted_row["id"]
            else:
                lastrowid = cursor.lastrowid

        db.commit()
        if hasattr(cursor, "close"):
            cursor.close()
        return lastrowid
    except Exception:
        if get_db_engine() == "postgres":
            try:
                db.rollback()
            except Exception:
                pass
        raise


def execute_many(sql, seq_of_params):
    """
    Executa um comando de escrita em lote.

    Parâmetros:
        sql (str): instrução SQL.
        seq_of_params (iterable): coleção de tuplas de parâmetros.

    Retorno:
        None.
    """
    db = get_db()
    db.executemany(convert_sql_placeholders(sql), seq_of_params)
    db.commit()


def init_db():
    """
    Cria as tabelas do banco caso ainda não existam.
    Para PostgreSQL, verifica se as tabelas existem e as recria se necessário.

    Parâmetros:
        Nenhum.

    Retorno:
        None.
    """
    db = get_db()
    schema_sql = get_schema_sql(get_db_engine())

    if get_db_engine() == "postgres":
        with db.cursor() as cursor:
            # # Try to drop all tables first (safe operation)
            # cursor.execute("DROP TABLE IF EXISTS manutencoes CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS movimentacoes CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS historico_chips CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS usuarios CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS empresas_suporte CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS niveis CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS centros_custo CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS estabelecimentos CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS tipos_linha CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS status_aparelho CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS usos_aparelho CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS grupos_whatsapp CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS colaboradores CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS descarte CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS devolvidos CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS estoque CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS chips CASCADE")
            # cursor.execute("DROP TABLE IF EXISTS aparelhos CASCADE")

            
            cursor.execute(schema_sql)
            cursor.execute(get_postgres_trigger_sql())
            
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")
    else:
        db.executescript(schema_sql)
        _ensure_sqlite_schema(db)

    db.commit()


def _ensure_sqlite_schema(db):
    """
    Garante que bancos SQLite antigos recebam colunas adicionadas depois.

    Parâmetros:
        db (sqlite3.Connection): conexão ativa do SQLite.

    Retorno:
        None.
    """
    existing_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(aparelhos)").fetchall()
    }
    for column_name, column_type in SQLITE_APARELHOS_OPTIONAL_COLUMNS.items():
        if column_name not in existing_columns:
            db.execute(f"ALTER TABLE aparelhos ADD COLUMN {column_name} {column_type}")

    # Ensure the usuarios table has the is_admin column
    existing_usuario_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(usuarios)").fetchall()
    }
    if "is_admin" not in existing_usuario_columns:
        db.execute("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Novos helpers de consulta
# - Ajustes de configuração da conexão SQLite/PostgreSQL
#
# Exige cuidado:
# - Mudanças em get_db, pois essa função é usada por todas as rotas
# - Conversão de placeholders SQL, pois impacta todas as queries do projeto
# - Alterações no commit automático, já que isso impacta consistência dos dados.
