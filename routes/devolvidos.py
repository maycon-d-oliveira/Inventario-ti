"""
Arquivo: routes/devolvidos.py
Proposito:
    Controlar aparelhos devolvidos, seus status e proximos destinos.
"""

import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from database import execute, query_all, query_one

from utils import log_movement

bp = Blueprint("devolvidos", __name__)


@bp.route("/", methods=["GET", "POST"])
def lista():
    """
    Lista aparelhos devolvidos e permite registrar novas devoluções.

    Parametros:
        Nenhum.

    Retorno:
        str: HTML da pagina de devolvidos.
    """
    if request.method == "POST":
        devolvido_id = execute(
            """
            INSERT INTO devolvidos (modelo, imei, antigo_usuario, unidade, observacao, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.form.get("modelo", "").strip() or None,
                request.form.get("imei", "").strip() or None,
                request.form.get("antigo_usuario", "").strip() or None,
                request.form.get("unidade", "").strip() or None,
                request.form.get("observacao", "").strip() or None,
                request.form.get("status", "").strip() or None,
            ),
        )
        log_movement("devolvidos", devolvido_id, "cadastro", "Nova devolução registrada.")
        flash("Devolução registrada com sucesso.", "success")
        return redirect(url_for("devolvidos.lista"))

    status = request.args.get("status", "").strip()
    if status:
        rows = query_all("SELECT * FROM devolvidos WHERE status = ? ORDER BY id DESC", (status,))
    else:
        rows = query_all("SELECT * FROM devolvidos ORDER BY id DESC")

    status_options = query_all("SELECT DISTINCT status FROM devolvidos WHERE status IS NOT NULL ORDER BY status")
    return render_template("devolvidos/lista.html", devolvidos=rows, status_options=status_options, filtro_status=status)


@bp.route("/<int:devolvido_id>/excluir", methods=["POST"])
def excluir(devolvido_id):
    """
    Exclui um registro devolvido.

    Parametros:
        devolvido_id (int): identificador do registro.

    Retorno:
        Response: redirecionamento para a listagem.
    """
    item = query_one("SELECT imei FROM devolvidos WHERE id = ?", (devolvido_id,))
    if not item:
        flash("Registro devolvido nao encontrado.", "error")
        return redirect(url_for("devolvidos.lista"))
    execute("DELETE FROM devolvidos WHERE id = ?", (devolvido_id,))
    log_movement("devolvidos", devolvido_id, "exclusao", f"Registro excluido: IMEI {item['imei'] or 'N/A'}.")
    flash("Registro excluido com sucesso.", "success")
    return redirect(url_for("devolvidos.lista"))


@bp.route("/excluir-multiplos", methods=["POST"])
def excluir_multiplos():
    """
    Exclui multiplos registros de devolvidos em massa.
    """
    ids = request.form.getlist("ids[]")
    if not ids:
        flash("Nenhum registro selecionado.", "warning")
        return redirect(url_for("devolvidos.lista"))
    count = 0
    for devolvido_id in ids:
        try:
            execute("DELETE FROM devolvidos WHERE id = ?", (devolvido_id,))
            count += 1
        except Exception:
            continue
    flash(f"{count} registro(s) excluido(s) com sucesso.", "success")
    return redirect(url_for("devolvidos.lista"))


@bp.route("/<int:devolvido_id>/para-estoque", methods=["POST"])
def para_estoque(devolvido_id):
    """
    Move um aparelho devolvido para a tabela de estoque.

    Parametros:
        devolvido_id (int): identificador do registro.

    Retorno:
        Response: redirecionamento para a tela de estoque.
    """
    item = query_one("SELECT * FROM devolvidos WHERE id = ?", (devolvido_id,))
    if not item:
        flash("Registro devolvido nao encontrado.", "error")
        return redirect(url_for("devolvidos.lista"))

    execute(
        """
        INSERT INTO estoque (unidade, marca, modelo, imei, centro_custo, observacoes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["unidade"],
            None,
            item["modelo"],
            item["imei"],
            None,
            item["observacao"],
            item["status"] or "DISPONÍVEL",
        ),
    )
    execute("DELETE FROM devolvidos WHERE id = ?", (devolvido_id,))
    log_movement("devolvidos", devolvido_id, "saida", "Aparelho devolvido encaminhado para estoque.")
    flash("Aparelho movido para o estoque.", "success")
    return redirect(url_for("estoque.lista"))


@bp.route("/<int:devolvido_id>/para-descarte", methods=["POST"])
def para_descarte(devolvido_id):
    """
    Move um aparelho devolvido para descarte eletronico.

    Parametros:
        devolvido_id (int): identificador do registro.

    Retorno:
        Response: redirecionamento para a tela de descarte.
    """
    item = query_one("SELECT * FROM devolvidos WHERE id = ?", (devolvido_id,))
    if not item:
        flash("Registro devolvido nao encontrado.", "error")
        return redirect(url_for("devolvidos.lista"))

    motivo = request.form.get("motivo", "").strip() or item["observacao"]
    data_descarte = request.form.get("data_descarte", "").strip() or None

    execute(
        """
        INSERT INTO descarte (modelo, imei, antigo_usuario, unidade, observacao, status, data_descarte)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["modelo"],
            item["imei"],
            item["antigo_usuario"],
            item["unidade"],
            motivo,
            item["status"],
            data_descarte,
        ),
    )
    execute("DELETE FROM devolvidos WHERE id = ?", (devolvido_id,))
    log_movement("devolvidos", devolvido_id, "saida", "Aparelho devolvido encaminhado para descarte.")
    flash("Aparelho movido para descarte.", "success")
    return redirect(url_for("descarte.lista"))


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta os devolvidos para CSV.

    Parametros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM devolvidos ORDER BY id DESC")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "modelo", "imei", "antigo_usuario", "unidade", "observacao", "status"])
    for row in rows:
        writer.writerow([row["id"], row["modelo"], row["imei"], row["antigo_usuario"], row["unidade"], row["observacao"], row["status"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=devolvidos.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com seguranca:
# - Lista de status aceitos
# - Campos do formulario de devolução
#
# Exige cuidado:
# - Fluxos para estoque e descarte, pois removem o registro original.
