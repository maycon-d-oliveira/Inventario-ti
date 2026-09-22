"""
Arquivo: routes/auxiliares.py
Proposito:
    Gerenciar listas auxiliares editaveis: estabelecimentos, tipos de linha,
    status, usos e niveis.
"""

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)

from database import execute, query_all, query_one

bp = Blueprint("auxiliares", __name__)

# Configuracao das tabelas auxiliares
AUX_TABLES = {
    "estabelecimentos": {
        "label": "Estabelecimentos",
        "columns": ["codigo", "descricao"],
        "labels": ["Codigo", "Descricao"],
        "types": ["text", "text"],
        "placeholders": ["Numero do estabelecimento", "Descricao"],
    },
    "tipos_linha": {
        "label": "Tipos de Linha",
        "columns": ["descricao"],
        "labels": ["Descricao"],
        "types": ["text"],
        "placeholders": ["Tipo de linha"],
    },
    "status_aparelho": {
        "label": "Status",
        "columns": ["descricao"],
        "labels": ["Descricao"],
        "types": ["text"],
        "placeholders": ["Status"],
    },
    "usos_aparelho": {
        "label": "Usos",
        "columns": ["descricao"],
        "labels": ["Descricao"],
        "types": ["text"],
        "placeholders": ["Uso"],
    },
    "niveis": {
        "label": "Niveis",
        "columns": ["descricao"],
        "labels": ["Descricao"],
        "types": ["text"],
        "placeholders": ["Nivel"],
    },
    "empresas_suporte": {
        "label": "Empresas de Suporte",
        "columns": ["descricao"],
        "labels": ["Descricao"],
        "types": ["text"],
        "placeholders": ["Nome da empresa/suporte"],
    },
}


@bp.route("/")
def lista_tabelas():
    """Lista todas as tabelas auxiliares e suas contagens."""
    tabelas = []
    for table_name, info in AUX_TABLES.items():
        count_row = query_one(f"SELECT COUNT(*) AS total FROM {table_name}")
        tabelas.append({
            "name": table_name,
            "label": info["label"],
            "count": count_row["total"] if count_row else 0,
        })
    return render_template("auxiliares/index.html", tabelas=tabelas)


@bp.route("/<table_name>/")
def lista_itens(table_name):
    """Lista os itens de uma tabela auxiliar."""
    if table_name not in AUX_TABLES:
        flash("Tabela nao encontrada.", "error")
        return redirect(url_for("auxiliares.lista_tabelas"))

    info = AUX_TABLES[table_name]
    itens = query_all(f"SELECT * FROM {table_name} ORDER BY descricao")
    return render_template(
        "auxiliares/lista.html",
        table_name=table_name,
        info=info,
        itens=itens,
    )


@bp.route("/<table_name>/novo", methods=["GET", "POST"])
def novo_item(table_name):
    """Cadastra um novo item em uma tabela auxiliar."""
    if table_name not in AUX_TABLES:
        flash("Tabela nao encontrada.", "error")
        return redirect(url_for("auxiliares.lista_tabelas"))

    info = AUX_TABLES[table_name]

    if request.method == "POST":
        values = []
        for col in info["columns"]:
            val = request.form.get(col, "").strip()
            values.append(val or None)

        placeholders = ", ".join(["?"] * len(info["columns"]))
        columns = ", ".join(info["columns"])
        try:
            execute(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
                tuple(values),
            )
            flash("Item cadastrado com sucesso.", "success")
            return redirect(url_for("auxiliares.lista_itens", table_name=table_name))
        except Exception as e:
            flash(f"Erro ao cadastrar: {e}", "error")

    return render_template(
        "auxiliares/form.html",
        table_name=table_name,
        info=info,
        item=None,
    )


@bp.route("/<table_name>/<int:item_id>/editar", methods=["GET", "POST"])
def editar_item(table_name, item_id):
    """Edita um item de uma tabela auxiliar."""
    if table_name not in AUX_TABLES:
        flash("Tabela nao encontrada.", "error")
        return redirect(url_for("auxiliares.lista_tabelas"))

    info = AUX_TABLES[table_name]
    item = query_one(f"SELECT * FROM {table_name} WHERE id = ?", (item_id,))
    if not item:
        flash("Item nao encontrado.", "error")
        return redirect(url_for("auxiliares.lista_itens", table_name=table_name))

    if request.method == "POST":
        updates = []
        values = []
        for col in info["columns"]:
            val = request.form.get(col, "").strip()
            updates.append(f"{col} = ?")
            values.append(val or None)
        values.append(item_id)

        try:
            execute(
                f"UPDATE {table_name} SET {', '.join(updates)} WHERE id = ?",
                tuple(values),
            )
            flash("Item atualizado com sucesso.", "success")
            return redirect(url_for("auxiliares.lista_itens", table_name=table_name))
        except Exception as e:
            flash(f"Erro ao atualizar: {e}", "error")

    return render_template(
        "auxiliares/form.html",
        table_name=table_name,
        info=info,
        item=item,
    )


@bp.route("/<table_name>/<int:item_id>/excluir", methods=["POST"])
def excluir_item(table_name, item_id):
    """Exclui um item de uma tabela auxiliar."""
    if table_name not in AUX_TABLES:
        flash("Tabela nao encontrada.", "error")
        return redirect(url_for("auxiliares.lista_tabelas"))

    try:
        execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        flash("Item excluido com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao excluir: {e}", "error")

    return redirect(url_for("auxiliares.lista_itens", table_name=table_name))
