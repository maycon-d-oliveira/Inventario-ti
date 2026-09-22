"""
Arquivo: routes/colaboradores.py
Proposito:
    Permitir busca de colaboradores por nome ou matricula e visualizar
    aparelhos vinculados ao colaborador encontrado.
    Tambem sincroniza funcionarios ativos do banco OpenEdge.
"""

import csv
import io
import json

from flask import Blueprint, Response, flash, render_template, request, url_for, redirect, current_app

from database import get_db_engine, query_all, query_one

from openedge_client import sync_employees_to_db, sync_from_json


bp = Blueprint("colaboradores", __name__)


def _build_colaboradores_query(has_filter):
    """
    Monta a consulta de colaboradores compatível com o banco ativo.

    Parâmetros:
        has_filter (bool): indica se a consulta terá cláusula WHERE.

    Retorno:
        str: SQL pronto para execução.
    """
    if get_db_engine() == "postgres":
        aparelhos_expr = "STRING_AGG(a.modelo || ' - ' || COALESCE(a.imei, 'Sem IMEI'), ' | ')"
        cartao_expr = "COALESCE(a.nr_cartao::TEXT, '')"
    else:
        aparelhos_expr = "GROUP_CONCAT(a.modelo || ' - ' || COALESCE(a.imei, 'Sem IMEI'), ' | ')"
        cartao_expr = "COALESCE(CAST(a.nr_cartao AS TEXT), '')"

    where_sql = "WHERE UPPER(c.nome) LIKE ? OR UPPER(COALESCE(c.matricula, '')) LIKE ?" if has_filter else ""
    return f"""
        SELECT c.*,
               COUNT(a.id) AS total_aparelhos,
               {aparelhos_expr} AS aparelhos_vinculados
        FROM colaboradores c
        LEFT JOIN aparelhos a
            ON UPPER(COALESCE(a.usuario, '')) = UPPER(COALESCE(c.nome, ''))
            OR {cartao_expr} = COALESCE(c.matricula, '')
        {where_sql}
        GROUP BY c.id
        ORDER BY c.nome
    """


@bp.route("/")
def busca():
    """
    Realiza a busca de colaboradores e seus aparelhos vinculados.

    Parametros:
        q (opcional): termo de busca por nome ou matricula.
        page (opcional): numero da pagina para paginacao (default 1).

    Retorno:
        str: HTML da tela de busca de colaboradores.
    """
    termo = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 50)

    # Build WHERE clause and params
    if termo:
        like = f"%{termo}%".upper()
        where_sql = "WHERE UPPER(c.nome) LIKE ? OR UPPER(COALESCE(c.matricula, '')) LIKE ?"
        params = (like, like)
        count_params = (like, like)
    else:
        where_sql = ""
        params = ()
        count_params = ()

    # Total count query
    count_sql = f"SELECT COUNT(*) AS total FROM colaboradores c {where_sql}"
    total_row = query_one(count_sql, count_params)
    total = total_row['total'] if total_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    # Clamp page to valid range
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    # Build main query with pagination
    # Reuse the existing query builder but add LIMIT/OFFSET
    main_query = _build_colaboradores_query(bool(termo))
    # Append LIMIT and OFFSET
    main_query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

    colaboradores = query_all(main_query, params)

    fim_da_pagina = min(page * per_page, total)
    
    return render_template("colaboradores/busca.html",
                           colaboradores=colaboradores,
                           termo=termo,
                           page=page,
                           fim_da_pagina=fim_da_pagina,
                           total_pages=total_pages,
                           total=total,
                           per_page=per_page)


@bp.route("/sincronizar", methods=["POST"])
def sincronizar():
    """
    Sincroniza funcionarios ativos do OpenEdge com a tabela colaboradores.

    Parametros:
        Nenhum.

    Retorno:
        Redirect: volta para a pagina de busca com mensagem de status.
    """
    try:
        relatorio = sync_employees_to_db()
        flash(
            f"Sincronizacao concluida: {relatorio['inserted']} inseridos, "
            f"{relatorio['updated']} atualizados. Total: {relatorio['total']}.",
            "success",
        )
    except Exception as e:
        flash(f"Erro na sincronizacao: {e}", "warning")
        flash("Dica: verifique se o arquivo openedge.jar existe e se o IP do OpenEdge esta acessivel.", "info")

    return redirect(url_for("colaboradores.busca"))


@bp.route("/importar-json", methods=["GET", "POST"])
def importar_json():
    """
    Importa funcionarios a partir de um arquivo JSON (alternativa ao JDBC).
    O JSON deve ser gerado pelo script func.py fora do Docker.

    Parametros:
        Nenhum (POST com arquivo JSON).

    Retorno:
        GET: formulario de upload.
        POST: processa arquivo e redireciona.
    """
    if request.method == "POST":
        if "json_file" not in request.files:
            flash("Nenhum arquivo enviado.", "error")
            return redirect(url_for("colaboradores.importar_json"))

        arquivo = request.files["json_file"]
        if not arquivo.filename.endswith(".json"):
            flash("Arquivo deve ser .json", "error")
            return redirect(url_for("colaboradores.importar_json"))

        try:
            json_data = json.load(arquivo)
            relatorio = sync_from_json(json_data)
            flash(
                f"Importacao concluida: {relatorio['inserted']} inseridos, "
                f"{relatorio['updated']} atualizados. Total: {relatorio['total']}.",
                "success",
            )
        except Exception as e:
            flash(f"Erro ao importar JSON: {e}", "error")

        return redirect(url_for("colaboradores.busca"))

    return render_template("colaboradores/importar_json.html")


@bp.route("/api/buscar-por-cartao/<nr_cartao>")
def buscar_por_cartao(nr_cartao):
    """
    API para buscar colaborador pelo numero do cartao (que corresponde a matricula).

    Parametros:
        nr_cartao (str): numero do cartao do colaborador (mesmo que matricula).

    Retorno:
        JSON: dados do colaborador ou erro 404.
    """
    from database import query_one

    colaborador = query_one(
        "SELECT * FROM colaboradores WHERE matricula = ?",
        (nr_cartao,),
    )

    if not colaborador:
        return {"situacao": "Desligado", "nome": "", "cargo": "", "estabelecimento": "", "centro_custo": "", "departamento": ""}

    situacao = "Desligado" if colaborador.get("data_desligamento") else "Ativo"

    return {
        "nome": colaborador.get("nome", ""),
        "cargo": colaborador.get("cargo", ""),
        "estabelecimento": colaborador.get("estabelecimento", ""),
        "centro_custo": colaborador.get("centro_custo", ""),
        "departamento": colaborador.get("departamento", ""),
        "situacao": situacao,
    }


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta a base de colaboradores para CSV.

    Parametros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM colaboradores ORDER BY nome")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "matricula",
            "nome",
            "estabelecimento",
            "cargo",
            "centro_custo",
            "departamento",
            "data_admissao",
            "data_desligamento",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["matricula"],
                row["nome"],
                row["estabelecimento"],
                row["cargo"],
                row["centro_custo"],
                row["departamento"],
                row["data_admissao"],
                row["data_desligamento"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=colaboradores.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com seguranca:
# - Criterios de busca por colaborador
# - Forma de vinculacao entre colaborador e aparelho
#
# Exige cuidado:
# - Regras de juncao entre colaborador e aparelho, pois dependem da qualidade
#   dos dados importados da planilha.
