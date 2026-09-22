"""
Arquivo: routes/descarte.py
Propósito:
    Registrar e consultar descartes eletrônicos com filtros simples.
"""

import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from database import execute, query_all

from utils import log_movement

bp = Blueprint("descarte", __name__)


@bp.route("/", methods=["GET", "POST"])
def lista():
    """
    Lista descartes e permite registrar novos itens manualmente.

    Parâmetros:
        Nenhum.

    Retorno:
        str: HTML da página de descarte.
    """
    if request.method == "POST":
        descarte_id = execute(
            """
            INSERT INTO descarte (modelo, imei, antigo_usuario, unidade, observacao, status, data_descarte)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.form.get("modelo", "").strip() or None,
                request.form.get("imei", "").strip() or None,
                request.form.get("antigo_usuario", "").strip() or None,
                request.form.get("unidade", "").strip() or None,
                request.form.get("observacao", "").strip() or None,
                request.form.get("status", "").strip() or None,
                request.form.get("data_descarte", "").strip() or None,
            ),
        )
        log_movement("descarte", descarte_id, "cadastro", "Novo descarte eletrônico registrado.")
        flash("Descarte registrado com sucesso.", "success")
        return redirect(url_for("descarte.lista"))

    unidade = request.args.get("unidade", "").strip()
    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()

    conditions = []
    params = []
    if unidade:
        conditions.append("unidade = ?")
        params.append(unidade)
    if data_inicio:
        conditions.append("date(data_descarte) >= date(?)")
        params.append(data_inicio)
    if data_fim:
        conditions.append("date(data_descarte) <= date(?)")
        params.append(data_fim)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    descartes = query_all(f"SELECT * FROM descarte {where_clause} ORDER BY data_descarte DESC, id DESC", tuple(params))
    unidades = query_all("SELECT DISTINCT unidade FROM descarte WHERE unidade IS NOT NULL ORDER BY unidade")
    return render_template("descarte/lista.html", descartes=descartes, unidades=unidades, filters=request.args)


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta o histórico de descarte para CSV.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM descarte ORDER BY data_descarte DESC, id DESC")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "modelo", "imei", "antigo_usuario", "unidade", "observacao", "status", "data_descarte"])
    for row in rows:
        writer.writerow([row["id"], row["modelo"], row["imei"], row["antigo_usuario"], row["unidade"], row["observacao"], row["status"], row["data_descarte"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=descarte.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Filtros por período e unidade
# - Campos opcionais do formulário
#
# Exige cuidado:
# - Tratamento de datas, para não quebrar consultas históricas.
