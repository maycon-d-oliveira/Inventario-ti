"""
Arquivo: routes/estoque.py
Proposito:
    Controlar aparelhos em estoque e movimentações entre estoque e inventário.
"""

import csv
import io

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from database import execute, query_all, query_one

from utils import log_movement

bp = Blueprint("estoque", __name__)


@bp.route("/")
def lista():
    """
    Lista aparelhos em estoque, opcionalmente filtrados por unidade, marca, modelo e status, com paginação.

    Parâmetros:
        Nenhum.

    Retorno:
        str: HTML da listagem de estoque.
    """
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    offset = (page - 1) * per_page

    conditions = []
    params = []

    unidade = request.args.get("unidade", "").strip()
    marca = request.args.get("marca", "").strip()
    modelo = request.args.get("modelo", "").strip()
    status = request.args.get("status", "").strip()

    if unidade:
        conditions.append("unidade = ?")
        params.append(unidade)
    if marca:
        conditions.append("marca LIKE ?")
        params.append(f"%{marca}%")
    if modelo:
        conditions.append("modelo LIKE ?")
        params.append(f"%{modelo}%")
    if status:
        conditions.append("status = ?")
        params.append(status)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    total_row = query_one(f"SELECT COUNT(*) AS total FROM estoque {where_clause}", tuple(params))
    total = total_row["total"]
    total_pages = max((total + per_page - 1) // per_page, 1)

    estoque = query_all(
        f"SELECT * FROM estoque {where_clause} ORDER BY unidade, id DESC LIMIT ? OFFSET ?",
        tuple(params + [per_page, offset]),
    )

    unidades = query_all("SELECT DISTINCT unidade FROM estoque WHERE unidade IS NOT NULL ORDER BY unidade")
    pagination_args = request.args.to_dict(flat=True)
    pagination_args.pop("page", None)

    return render_template(
        "estoque/lista.html",
        estoque=estoque,
        unidades=unidades,
        filtro_unidade=unidade,
        filtro_marca=marca,
        filtro_modelo=modelo,
        filtro_status=status,
        page=page,
        total_pages=total_pages,
        total=total,
        pagination_args=pagination_args,
    )


@bp.route("/<int:estoque_id>/mover-para-inventario", methods=["POST"])
def mover_para_inventario(estoque_id):
    """
    Move um aparelho do estoque para o inventário principal.

    Parâmetros:
        estoque_id (int): identificador do item em estoque.

    Retorno:
        Response: redirecionamento para a tela de estoque.
    """
    item = query_one("SELECT * FROM estoque WHERE id = ?", (estoque_id,))
    if not item:
        flash("Item de estoque não encontrado.", "error")
        return redirect(url_for("estoque.lista"))

    usuario = request.form.get("usuario", "").strip() or None
    responsavel = request.form.get("responsavel", "").strip() or usuario
    uso = request.form.get("uso", "").strip() or "INDIVIDUAL"
    status = request.form.get("status", "").strip() or "EM USO"

    aparelho_id = execute(
        """
        INSERT INTO aparelhos (
            estab, marca, modelo, imei, centro_custo, observacoes,
            usuario, responsavel, uso, status
        )
        VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?)
        """,
        (
            item["unidade"],
            item["marca"],
            item["modelo"],
            item["imei"],
            item["centro_custo"],
            item["observacoes"],
            usuario,
            responsavel,
            uso,
            status,
        ),
    )
    execute("DELETE FROM estoque WHERE id = ?", (estoque_id,))
    log_movement("estoque", estoque_id, "saida", f"Aparelho IMEI {item['imei']} movido do estoque para o inventário.")
    log_movement("aparelhos", aparelho_id, "entrada", f"Aparelho recebido do estoque para usuário {usuario or 'não informado'}.")
    flash("Aparelho movido para o inventário com sucesso.", "success")
    return redirect(url_for("inventario.ficha", aparelho_id=aparelho_id))


@bp.route("/<int:estoque_id>/excluir", methods=["POST"])
def excluir(estoque_id):
    """
    Exclui um item do estoque.

    Parâmetros:
        estoque_id (int): identificador do item em estoque.

    Retorno:
        Response: redirecionamento para a tela de estoque.
    """
    item = query_one("SELECT imei FROM estoque WHERE id = ?", (estoque_id,))
    if not item:
        flash("Item de estoque não encontrado.", "error")
        return redirect(url_for("estoque.lista"))
    execute("DELETE FROM estoque WHERE id = ?", (estoque_id,))
    log_movement("estoque", estoque_id, "exclusao", f"Item excluído do estoque: IMEI {item['imei'] or 'N/A'}.")
    flash("Item excluído com sucesso.", "success")
    return redirect(url_for("estoque.lista"))


@bp.route("/excluir-multiplos", methods=["POST"])
def excluir_multiplos():
    """
    Exclui múltiplos itens do estoque em massa.

    Parâmetros:
        Nenhum (recebe lista de IDs via formulário).

    Retorno:
        Response: redirecionamento para a tela de estoque.
    """
    ids = request.form.getlist("ids[]")
    if not ids:
        flash("Nenhum item selecionado.", "warning")
        return redirect(url_for("estoque.lista"))
    count = 0
    for estoque_id in ids:
        try:
            execute("DELETE FROM estoque WHERE id = ?", (estoque_id,))
            count += 1
        except Exception:
            continue
    flash(f"{count} item(s) excluído(s) com sucesso.", "success")
    return redirect(url_for("estoque.lista"))


@bp.route("/inventario/<int:aparelho_id>/retornar", methods=["POST"])
def retornar_para_estoque(aparelho_id):
    """
    Move um aparelho do inventário para o estoque.

    Parâmetros:
        aparelho_id (int): identificador do aparelho no inventário.

    Retorno:
        Response: redirecionamento para a tela de estoque.
    """
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (aparelho_id,))
    if not aparelho:
        flash("Aparelho não encontrado no inventário.", "error")
        return redirect(url_for("estoque.lista"))

    execute(
        """
        INSERT INTO estoque (unidade, marca, modelo, imei, centro_custo, observacoes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            aparelho["estab"],
            aparelho["marca"],
            aparelho["modelo"],
            aparelho["imei"],
            aparelho["centro_custo"],
            aparelho["observacoes"],
            "DISPONÍVEL",
        ),
    )
    execute("DELETE FROM aparelhos WHERE id = ?", (aparelho_id,))
    log_movement("aparelhos", aparelho_id, "saida", f"Aparelho IMEI {aparelho['imei']} devolvido ao estoque.")
    flash("Aparelho retornou ao estoque.", "success")
    return redirect(url_for("estoque.lista"))


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta o estoque para CSV.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM estoque ORDER BY unidade, id DESC")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "unidade", "marca", "modelo", "imei", "centro_custo", "observacoes", "status"])
    for row in rows:
        writer.writerow([row["id"], row["unidade"], row["marca"], row["modelo"], row["imei"], row["centro_custo"], row["observacoes"], row["status"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=estoque.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Campos coletados na movimentação para inventário
# - Filtros simples por unidade
#
# Exige cuidado:
# - Processo de mover registros entre tabelas, pois removem a origem.
