"""
Arquivo: openedge_client.py
Proposito:
    Conectar no banco OpenEdge via JDBC e sincronizar funcionarios
    ativos com a tabela colaboradores da aplicacao.
"""

import logging

import jaydebeapi

from flask import current_app


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mapeamento de colunas do OpenEdge para a tabela colaboradores
COLUMN_MAP = {
    "num_pessoa_fisic": "matricula",
    "nom_pessoa_fisic": "nome",
    "cdn_estab": "estabelecimento",
    "des_cargo": "cargo",
    "cod_rh_ccusto": "centro_custo",
    "des_unid_lotac": "departamento",
}


def get_openedge_connection():
    """
    Estabelece conexao com o banco OpenEdge usando jaydebeapi.
    O jaydebeapi cuida da inicializacao da JVM e classpath.

    Retorno:
        Connection: objeto de conexao JDBC.
    """
    jdbc_driver = current_app.config.get("OPENEDGE_DRIVER", "com.ddtek.jdbc.openedge.OpenEdgeDriver")
    jar_path = current_app.config.get("OPENEDGE_JAR", "/app/openedge.jar")
    url = current_app.config.get(
        "OPENEDGE_URL", "jdbc:datadirect:openedge://172.0.0.217:23607;databaseName=hcm"
    )
    user = current_app.config.get("OPENEDGE_USER", "sysprogress")
    password = current_app.config.get("OPENEDGE_PASSWORD", "sysprogress")

    logger.info("Conectando ao OpenEdge: %s", url)

    try:
        conn = jaydebeapi.connect(
            jdbc_driver,
            url,
            [user, password],
            jar_path
        )
        logger.info("Conexao estabelecida com sucesso")
        return conn
    except Exception as e:
        logger.error("Falha ao conectar: %s", str(e))
        raise RuntimeError(
            f"Nao foi possivel conectar ao OpenEdge. "
            f"Verifique se o arquivo {jar_path} existe e "
            f"contem a classe {jdbc_driver}, e se o IP "
            f"172.0.0.217:23607 esta acessivel."
        ) from e


def fetch_active_employees():
    """
    Consulta funcionarios ativos no OpenEdge com dados mais recentes.

    Retorno:
        list[dict]: lista de dicionarios com dados dos funcionarios.
    """
    sql = """
    
    SELECT
        fcs.num_pessoa_fisic,
        fcs.nom_pessoa_fisic,
        fcs.cdn_estab,
        c.des_cargo,
        fcs.cod_rh_ccusto,
        UPPER(ul.des_unid_lotac) AS des_unid_lotac,
        f.dat_desligto_func,
        f.dat_admis_func
    FROM (
        /* Reduzimos a fcs antes de qualquer JOIN */
        SELECT f1.*
        FROM PUB.func_cargo_salario f1
        INNER JOIN (
            SELECT num_pessoa_fisic, MAX(dat_ult_atualiz) as max_atualiz
            FROM PUB.func_cargo_salario
            GROUP BY num_pessoa_fisic
        ) f2 ON f1.num_pessoa_fisic = f2.num_pessoa_fisic 
            AND f1.dat_ult_atualiz = f2.max_atualiz
    ) fcs


    INNER JOIN (
        SELECT f_orig.*
        FROM PUB.funcionario f_orig
        INNER JOIN (
            SELECT num_pessoa_fisic, MAX(dat_admis_func) as max_adm
            FROM PUB.funcionario
            GROUP BY num_pessoa_fisic
        ) f_max ON f_orig.num_pessoa_fisic = f_max.num_pessoa_fisic 
                AND f_orig.dat_admis_func = f_max.max_adm
    ) f ON f.num_pessoa_fisic = fcs.num_pessoa_fisic


    LEFT JOIN PUB.cargo c ON 
        fcs.cdn_cargo_basic = c.cdn_cargo_basic AND 
        fcs.cdn_niv_cargo = c.cdn_niv_cargo

    LEFT JOIN PUB.unid_lotac ul ON 
        fcs.cod_unid_lotac = ul.cod_unid_lotac

    WHERE 
        (f.dat_desligto_func IS NULL OR NOT EXISTS (
            SELECT 1 FROM PUB.funcionario f_check 
            WHERE f_check.num_pessoa_fisic = f.num_pessoa_fisic 
            AND f_check.dat_admis_func = f.dat_admis_func 
            AND f_check.dat_desligto_func IS NULL
        ))
    """
    # QUERY ANTIGA-----------------------
    #  SELECT
    #     fcs.num_pessoa_fisic,
    #     fcs.nom_pessoa_fisic,
    #     fcs.cdn_estab,
    #     c.des_cargo,
    #     fcs.cod_rh_ccusto,
    #     UPPER(ul.des_unid_lotac) AS des_unid_lotac,
    #     dat_desligto_func
    # FROM PUB.func_cargo_salario fcs
    # INNER JOIN (
    #     SELECT num_pessoa_fisic, MAX(dat_ult_atualiz) AS max_data
    #     FROM PUB.func_cargo_salario
    #     GROUP BY num_pessoa_fisic
    # ) ult ON fcs.num_pessoa_fisic = ult.num_pessoa_fisic
    #     AND fcs.dat_ult_atualiz = ult.max_data
    # LEFT JOIN PUB.cargo c ON fcs.cdn_cargo_basic = c.cdn_cargo_basic
    #     AND fcs.cdn_niv_cargo = c.cdn_niv_cargo
    # LEFT JOIN PUB.unid_lotac ul ON fcs.cod_unid_lotac = ul.cod_unid_lotac
    # LEFT JOIN PUB.FUNCIONARIO f ON fcs.num_pessoa_fisic = f.num_pessoa_fisic
    # WHERE f.dat_desligto_func IS NULL
    
    
    conn = get_openedge_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        columns = [desc[0].lower() for desc in cursor.description]
        logger.info("Colunas retornadas pelo OpenEdge: %s", columns)
        rows = cursor.fetchall()
        employees = [dict(zip(columns, row)) for row in rows]
        logger.info("Primeiro funcionario: %s", employees[0] if employees else "Nenhum")
        return employees
    finally:
        cursor.close()
        conn.close()


def sync_employees_to_db():
    """
    Sincroniza funcionarios ativos do OpenEdge para a tabela colaboradores.

    Retorno:
        dict: relatorio com total de inseridos/atualizados.
    """
    from database import execute, query_one

    try:
        employees = fetch_active_employees()
    except Exception as e:
        logger.error("Erro ao buscar funcionarios: %s", str(e))
        raise

    inserted = 0
    updated = 0

    for emp in employees:
        # Handle case-insensitive column access from OpenEdge
        matricula = emp.get("num_pessoa_fisic") or emp.get("NUM_PESSOA_FISIC")
        nome = emp.get("nom_pessoa_fisic") or emp.get("NOM_PESSOA_FISIC")
        estab = emp.get("cdn_estab") or emp.get("CDN_ESTAB")
        cargo = emp.get("des_cargo") or emp.get("DES_CARGO")
        centro_custo = emp.get("cod_rh_ccusto") or emp.get("COD_RH_CCUSTO")
        departamento = emp.get("des_unid_lotac") or emp.get("DES_UNID_LOTAC")
        data_desligamento = emp.get("dat_desligto_func") or emp.get("DAT_DESLIGTO_FUNC")

        if not matricula:
            continue

        # Convert matricula to string for database comparison
        matricula_str = str(matricula)

        existing = query_one(
            "SELECT id FROM colaboradores WHERE matricula = ?",
            (matricula_str,),
        )

        if existing:
            execute(
                """
                UPDATE colaboradores
                SET nome = ?, estabelecimento = ?, cargo = ?,
                    centro_custo = ?, departamento = ?, data_desligamento = ?
                WHERE id = ?
                """,
                (nome, estab, cargo, centro_custo, departamento, data_desligamento, existing["id"]),
            )
            updated += 1
        else:
            execute(
                """
                INSERT INTO colaboradores
                (matricula, nome, estabelecimento, cargo, centro_custo, departamento, data_desligamento)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (matricula_str, nome, estab, cargo, centro_custo, departamento, data_desligamento),
            )
            inserted += 1

    return {"inserted": inserted, "updated": updated, "total": len(employees)}


def sync_from_json(json_data):
    """
    Sincroniza funcionarios a partir de um JSON (alternativa ao JDBC).

    Parametros:
        json_data (list[dict]): lista de dicionarios com dados dos funcionarios.

    Retorno:
        dict: relatorio com total de inseridos/atualizados.
    """
    from database import execute, query_one

    inserted = 0
    updated = 0

    for emp in json_data:
        matricula = emp.get("num_pessoa_fisic") or emp.get("matricula")
        if not matricula:
            continue

        nome = emp.get("nom_pessoa_fisic") or emp.get("nome")
        estab = emp.get("cdn_estab") or emp.get("estabelecimento")
        cargo = emp.get("des_cargo") or emp.get("cargo")
        centro_custo = emp.get("cod_rh_ccusto") or emp.get("centro_custo")
        departamento = emp.get("des_unid_lotac") or emp.get("departamento")

        existing = query_one(
            "SELECT id FROM colaboradores WHERE matricula = ?",
            (matricula,),
        )

        if existing:
            execute(
                """
                UPDATE colaboradores
                SET nome = ?, estabelecimento = ?, cargo = ?,
                    centro_custo = ?, departamento = ?, data_desligamento = NULL
                WHERE id = ?
                """,
                (nome, estab, cargo, centro_custo, departamento, existing["id"]),
            )
            updated += 1
        else:
            execute(
                """
                INSERT INTO colaboradores
                (matricula, nome, estabelecimento, cargo, centro_custo, departamento)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (matricula, nome, estab, cargo, centro_custo, departamento),
            )
            inserted += 1

    return {"inserted": inserted, "updated": updated, "total": len(json_data)}
