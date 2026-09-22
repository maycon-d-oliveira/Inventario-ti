"""
Arquivo: routes/chips.py
Propósito:
    Implementar a gestão de chips, filtros, vínculo com aparelhos e histórico.
"""

import csv
import io

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from database import execute, query_all, query_one

from utils import log_movement

bp = Blueprint("chips", __name__)


@bp.route("/")
def lista():
    """
    Lista chips com filtros por status, linha e ICCID, com paginação.

    Parâmetros:
        Nenhum.

    Retorno:
        str: HTML da listagem de chips.
    """
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    offset = (page - 1) * per_page

    conditions = []
    params = []

    status = request.args.get("status", "").strip()
    linha = request.args.get("linha", "").strip()
    chip_iccid = request.args.get("chip", "").strip()

    if status:
        conditions.append("status = ?")
        params.append(status)
    if linha:
        conditions.append("linha LIKE ?")
        params.append(f"%{linha}%")
    if chip_iccid:
        conditions.append("chip LIKE ?")
        params.append(f"%{chip_iccid}%")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    total_row = query_one(f"SELECT COUNT(*) AS total FROM chips {where_clause}", tuple(params))
    total = total_row["total"]
    total_pages = max((total + per_page - 1) // per_page, 1)

    chips = query_all(
        f"SELECT * FROM chips {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        tuple(params + [per_page, offset]),
    )
    # Busca o aparelho vinculado a cada chip (por ICCID ou linha)
    for chip in chips:
        aparelho = query_one(
            "SELECT id, usuario, modelo FROM aparelhos WHERE chip = ? OR linha = ? LIMIT 1",
            (chip["chip"], chip["linha"]),
        )
        chip["aparelho_vinculado"] = aparelho
    status_options = query_all("SELECT DISTINCT status FROM chips WHERE status IS NOT NULL ORDER BY status")

    pagination_args = request.args.to_dict(flat=True)
    pagination_args.pop("page", None)

    return render_template(
        "chips/lista.html",
        chips=chips,
        status_options=status_options,
        page=page,
        total_pages=total_pages,
        total=total,
        pagination_args=pagination_args,
    )


@bp.route("/<int:chip_id>/vincular", methods=["POST"])
def vincular(chip_id):
    """
    Vincula um chip existente a um aparelho do inventário.

    Parâmetros:
        chip_id (int): identificador do chip.

    Retorno:
        Response: redirecionamento para a tela de chips.
    """
    aparelho_id = request.form.get("aparelho_id", type=int)
    chip = query_one("SELECT * FROM chips WHERE id = ?", (chip_id,))
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (aparelho_id,))

    if not chip or not aparelho:
        flash("Chip ou aparelho não encontrado.", "error")
        return redirect(url_for("chips.lista"))

    execute("UPDATE aparelhos SET chip = ?, linha = COALESCE(linha, ?) WHERE id = ?", (chip["chip"], chip["linha"], aparelho_id))
    execute(
        """
        INSERT INTO historico_chips (chip, aparelho_id, imei, linha, observacao)
        VALUES (?, ?, ?, ?, ?)
        """,
        (chip["chip"], aparelho_id, aparelho["imei"], chip["linha"], "Vinculado manualmente pela gestão de chips."),
    )
    log_movement("chips", chip_id, "vinculo", f"Chip {chip['chip']} vinculado ao aparelho {aparelho_id}.")
    flash("Chip vinculado ao aparelho com sucesso.", "success")
    return redirect(url_for("chips.lista"))


@bp.route("/<int:chip_id>/excluir", methods=["POST"])
def excluir(chip_id):
    """
    Exclui um chip.

    Parâmetros:
        chip_id (int): identificador do chip.

    Retorno:
        Response: redirecionamento para a tela de chips.
    """
    chip = query_one("SELECT chip FROM chips WHERE id = ?", (chip_id,))
    if not chip:
        flash("Chip não encontrado.", "error")
        return redirect(url_for("chips.lista"))
    # Remove vínculo no inventário
    execute("UPDATE aparelhos SET chip = NULL WHERE chip = ?", (chip["chip"],))
    execute("DELETE FROM historico_chips WHERE chip = ?", (chip["chip"],))
    execute("DELETE FROM chips WHERE id = ?", (chip_id,))
    log_movement("chips", chip_id, "exclusao", f"Chip {chip['chip']} excluído.")
    flash("Chip excluído com sucesso.", "success")
    return redirect(url_for("chips.lista"))


@bp.route("/excluir-multiplos", methods=["POST"])
def excluir_multiplos():
    """
    Exclui múltiplos chips em massa.

    Parâmetros:
        Nenhum (recebe lista de IDs via formulário).

    Retorno:
        Response: redirecionamento para a tela de chips.
    """
    ids = request.form.getlist("ids[]")
    if not ids:
        flash("Nenhum chip selecionado.", "warning")
        return redirect(url_for("chips.lista"))
    count = 0
    for chip_id in ids:
        try:
            chip = query_one("SELECT chip FROM chips WHERE id = ?", (chip_id,))
            if chip:
                execute("UPDATE aparelhos SET chip = NULL WHERE chip = ?", (chip["chip"],))
                execute("DELETE FROM historico_chips WHERE chip = ?", (chip["chip"],))
                execute("DELETE FROM chips WHERE id = ?", (chip_id,))
                count += 1
        except Exception:
            continue
    flash(f"{count} chip(s) excluído(s) com sucesso.", "success")
    return redirect(url_for("chips.lista"))


@bp.route("/<int:chip_id>/ficha")
def ficha(chip_id):
    """
    Exibe a ficha completa de um chip: dados, aparelho vinculado e histórico.

    Parâmetros:
        chip_id (int): identificador do chip.

    Retorno:
        str | Response: HTML da ficha ou redirecionamento em caso de erro.
    """
    chip = query_one("SELECT * FROM chips WHERE id = ?", (chip_id,))
    if not chip:
        flash("Chip não encontrado.", "error")
        return redirect(url_for("chips.lista"))

    # Busca o aparelho vinculado (por ICCID ou linha)
    aparelho_vinculado = query_one(
        "SELECT id, usuario, modelo, imei FROM aparelhos WHERE chip = ? OR linha = ? LIMIT 1",
        (chip["chip"], chip["linha"]),
    )

    # Busca o histórico de vinculações
    historico = query_all(
        """
        SELECT h.*, a.usuario, a.modelo, a.imei
        FROM historico_chips h
        LEFT JOIN aparelhos a ON a.id = h.aparelho_id
        WHERE h.chip = ?
        ORDER BY h.data_vinculo DESC, h.id DESC
        """,
        (chip["chip"],),
    )

    return render_template(
        "chips/ficha.html",
        chip=chip,
        aparelho_vinculado=aparelho_vinculado,
        historico=historico,
    )


@bp.route("/<int:chip_id>/historico")
def historico(chip_id):
    """
    Redireciona para a ficha do chip (manter compatibilidade).
    """
    return redirect(url_for("chips.ficha", chip_id=chip_id))


@bp.route("/<int:chip_id>/editar", methods=["GET", "POST"])
def editar(chip_id):
    """
    Edita os dados de um chip.

    Parâmetros:
        chip_id (int): identificador do chip.

    Retorno:
        Response: redirecionamento para a tela de chips ou formulário de edição.
    """
    chip = query_one("SELECT * FROM chips WHERE id = ?", (chip_id,))
    if not chip:
        flash("Chip não encontrado.", "error")
        return redirect(url_for("chips.lista"))

    if request.method == "POST":
        # Obtém os dados do formulário
        linha = request.form.get("linha", "").strip()
        chip_iccid = request.form.get("chip", "").strip()
        status = request.form.get("status", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        # Validação básica
        if not linha:
            flash("O número da linha é obrigatório.", "error")
            return render_template("chips/editar.html", chip=chip)

        # Atualiza o chip
        execute(
            "UPDATE chips SET linha = ?, chip = ?, status = ?, observacoes = ? WHERE id = ?",
            (linha, chip_iccid, status, observacoes, chip_id)
        )

        flash("Chip atualizado com sucesso.", "success")
        return redirect(url_for("chips.lista"))

    return render_template("chips/editar.html", chip=chip)


@bp.route("/api/buscar-por-linha/<linha>")
def buscar_por_linha(linha):
    """
    API: busca chip vinculado a uma linha específica.

    Parâmetros:
        linha (str): número da linha para buscar o chip.

    Retorno:
        Response: JSON com dados do chip ou erro 404.
    """
    from flask import jsonify
    chip = query_one(
        "SELECT id, linha, chip, status FROM chips WHERE linha = ? ORDER BY id DESC LIMIT 1",
        (linha,)
    )
    if not chip:
        return jsonify({"found": False}), 404
    return jsonify({
        "found": True,
        "id": chip["id"],
        "linha": chip["linha"],
        "chip": chip["chip"],
        "status": chip["status"]
    })


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta a listagem de chips para CSV.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM chips ORDER BY id DESC")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "linha", "chip", "status", "observacoes"])
    for row in rows:
        writer.writerow([row["id"], row["linha"], row["chip"], row["status"], row["observacoes"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=chips.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Filtros da listagem
# - Visualização do histórico
#
# Exige cuidado:
# - Processo de vinculação, pois ele altera dados do aparelho e do histórico.
