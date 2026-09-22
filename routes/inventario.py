"""
Arquivo: routes/inventario.py
Propósito:
    Implementar listagem, cadastro, edição, visualização e exportação do
    inventário principal de aparelhos.
"""

import csv
import io

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from openpyxl import Workbook

from database import execute, query_all, query_one

from utils import log_movement, sync_chip_with_device

bp = Blueprint("inventario", __name__)

APARELHO_FIELDS = [
    "linha",
    "estab",
    "mdm_id",
    "tipo_linha",
    "status",
    "uso",
    "usuario",
    "nivel",
    "nr_cartao",
    "responsavel",
    "cargo",
    "situacao",
    "centro_custo",
    "departamento",
    "internet",
    "grupo",
    "marca",
    "modelo_mdm",
    "modelo",
    "imei_mdm",
    "imei",
    "chip",
    "mac_wifi",
    "serial",
    "conta_google",
    "observacoes",
]


def _normalize_form_value(field_name):
    """
    Lê e normaliza um campo do formulário HTTP.

    Parâmetros:
        field_name (str): nome do campo enviado no formulário.

    Retorno:
        str | None: valor tratado sem espaços extras ou None se vazio.
    """
    value = request.form.get(field_name, "").strip()
    return value or None


def _build_inventory_filters():
    """
    Monta a cláusula WHERE dinâmica da listagem de inventário.

    Parâmetros:
        Nenhum.

    Retorno:
        tuple[str, list]: SQL do filtro e lista de parâmetros.
    """
    conditions = []
    params = []

    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        conditions.append(
            """
            (
                linha LIKE ? OR usuario LIKE ? OR imei LIKE ? OR
                responsavel LIKE ? OR modelo LIKE ? OR chip LIKE ?
            )
            """
        )
        params.extend([like, like, like, like, like, like])

    for column in ["status", "tipo_linha", "marca", "uso", "estab"]:
        value = request.args.get(column, "").strip()
        if value:
            conditions.append(f"{column} = ?")
            params.append(value)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params


@bp.route("/")
def lista():
    """
    Exibe a listagem paginada e filtrável do inventário.

    Parâmetros:
        Nenhum.

    Retorno:
        str: HTML renderizado com a tabela do inventário.
    """
    page = max(request.args.get("page", default=1, type=int), 1)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    offset = (page - 1) * per_page

    sort_by = request.args.get("sort_by", "").strip()
    order = request.args.get("order", "desc").strip().lower()

    # Valida coluna de ordenacao
    allowed_sort = ["id", "linha", "usuario", "modelo", "imei", "status", "updated_at", "created_at"]
    if sort_by not in allowed_sort:
        sort_by = "updated_at"
        order = "desc"
    if order not in ("asc", "desc"):
        order = "desc"

    where_clause, params = _build_inventory_filters()
    total_row = query_one(f"SELECT COUNT(*) AS total FROM aparelhos {where_clause}", tuple(params))
    order_clause = f"ORDER BY {sort_by} {order.upper()}, id {order.upper()}"
    aparelhos = query_all(
        f"""
        SELECT *
        FROM aparelhos
        {where_clause}
        {order_clause}
        LIMIT ? OFFSET ?
        """,
        tuple(params + [per_page, offset]),
    )

    filter_options = {
        "status": query_all("SELECT DISTINCT status FROM aparelhos WHERE status IS NOT NULL ORDER BY status"),
        "tipos_linha": query_all(
            "SELECT DISTINCT tipo_linha FROM aparelhos WHERE tipo_linha IS NOT NULL ORDER BY tipo_linha"
        ),
        "marcas": query_all("SELECT DISTINCT marca FROM aparelhos WHERE marca IS NOT NULL ORDER BY marca"),
        "usos": query_all("SELECT DISTINCT uso FROM aparelhos WHERE uso IS NOT NULL ORDER BY uso"),
        "unidades": query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo"),
    }

    total = total_row["total"]
    total_pages = max((total + per_page - 1) // per_page, 1)
    pagination_args = request.args.to_dict(flat=True)
    pagination_args.pop("page", None)

    return render_template(
        "inventario/lista.html",
        aparelhos=aparelhos,
        page=page,
        total_pages=total_pages,
        total=total,
        filters=request.args,
        filter_options=filter_options,
        pagination_args=pagination_args,
        sort_by=sort_by,
        order=order,
    )


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    """
    Cadastra um novo aparelho no inventário.

    Parâmetros:
        Nenhum.

    Retorno:
        str | Response: formulário HTML ou redirecionamento após salvar.
    """
    if request.method == "POST":
        data = [_normalize_form_value(field) for field in APARELHO_FIELDS]
        placeholders = ", ".join(["?"] * len(APARELHO_FIELDS))
        columns = ", ".join(APARELHO_FIELDS)

        aparelho_id = execute(
            f"INSERT INTO aparelhos ({columns}) VALUES ({placeholders})",
            tuple(data),
        )
        form_data = dict(zip(APARELHO_FIELDS, data))
        sync_chip_with_device(aparelho_id, form_data["linha"], form_data["chip"], form_data["imei"])
        log_movement(
            "aparelhos",
            aparelho_id,
            "cadastro",
            f"Aparelho cadastrado para usuário {form_data.get('usuario') or 'não informado'}.",
        )
        flash("Aparelho cadastrado com sucesso.", "success")
        return redirect(url_for("inventario.ficha", aparelho_id=aparelho_id))

    return render_template(
        "inventario/form.html",
        aparelho=None,
        estabelecimentos=query_all("SELECT * FROM estabelecimentos ORDER BY codigo"),
        tipos_linha=query_all("SELECT * FROM tipos_linha ORDER BY descricao"),
        status_list=query_all("SELECT * FROM status_aparelho ORDER BY descricao"),
        usos_list=query_all("SELECT * FROM usos_aparelho ORDER BY descricao"),
        niveis_list=query_all("SELECT * FROM niveis ORDER BY descricao"),
    )


@bp.route("/<int:aparelho_id>/editar", methods=["GET", "POST"])
def editar(aparelho_id):
    """
    Edita um aparelho já existente.

    Parâmetros:
        aparelho_id (int): identificador do aparelho.

    Retorno:
        str | Response: formulário HTML ou redirecionamento após salvar.
    """
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (aparelho_id,))
    if not aparelho:
        flash("Aparelho não encontrado.", "error")
        return redirect(url_for("inventario.lista"))

    if request.method == "POST":
        data = [_normalize_form_value(field) for field in APARELHO_FIELDS]
        assignments = ", ".join(f"{field} = ?" for field in APARELHO_FIELDS)
        execute(
            f"UPDATE aparelhos SET {assignments} WHERE id = ?",
            tuple(data + [aparelho_id]),
        )
        form_data = dict(zip(APARELHO_FIELDS, data))
        
        sync_chip_with_device(aparelho_id, form_data["linha"], form_data["chip"], form_data["imei"])
        log_movement(
            "aparelhos",
            aparelho_id,
            "edicao",
            f"Aparelho {aparelho_id} atualizado para usuário {form_data.get('usuario') or 'não informado'}.",
        )
        flash("Aparelho atualizado com sucesso.", "success")
        return redirect(url_for("inventario.ficha", aparelho_id=aparelho_id))

    return render_template(
        "inventario/form.html",
        aparelho=aparelho,
        estabelecimentos=query_all("SELECT * FROM estabelecimentos ORDER BY codigo"),
        tipos_linha=query_all("SELECT * FROM tipos_linha ORDER BY descricao"),
        status_list=query_all("SELECT * FROM status_aparelho ORDER BY descricao"),
        usos_list=query_all("SELECT * FROM usos_aparelho ORDER BY descricao"),
        niveis_list=query_all("SELECT * FROM niveis ORDER BY descricao"),
    )


@bp.route("/<int:aparelho_id>")
def ficha(aparelho_id):
    """
    Exibe a ficha completa de um aparelho.

    Parâmetros:
        aparelho_id (int): identificador do aparelho.

    Retorno:
        str | Response: HTML da ficha ou redirecionamento.
    """
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (aparelho_id,))
    if not aparelho:
        flash("Aparelho não encontrado.", "error")
        return redirect(url_for("inventario.lista"))

    historico_chip = query_all(
        """
        SELECT chip, imei, linha, data_vinculo, observacao
        FROM historico_chips
        WHERE aparelho_id = ?
        ORDER BY data_vinculo DESC, id DESC
        """,
        (aparelho_id,),
    )

    # Busca histórico de manutenções do aparelho
    historico_manutencao = query_all(
        """
        SELECT m.*, e.descricao as unidade_descricao
        FROM manutencoes m
        LEFT JOIN estabelecimentos e ON m.estab = e.codigo
        WHERE m.aparelho_id = ?
        ORDER BY m.created_at DESC
        """,
        (aparelho_id,),
    )

    # Busca dados do chip se a linha estiver preenchida
    chip_data = None
    if aparelho["linha"]:
        chip_data = query_one(
            "SELECT * FROM chips WHERE linha = ? ORDER BY id DESC LIMIT 1",
            (aparelho["linha"],),
        )

    return render_template(
        "inventario/ficha.html",
        aparelho=aparelho,
        historico_chip=historico_chip,
        historico_manutencao=historico_manutencao,
        chip_data=chip_data,
    )


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta a listagem atual do inventário para CSV.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    where_clause, params = _build_inventory_filters()
    rows = query_all(
        f"SELECT * FROM aparelhos {where_clause} ORDER BY updated_at DESC, id DESC",
        tuple(params),
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id"] + APARELHO_FIELDS + ["created_at", "updated_at"])
    for row in rows:
        writer.writerow([row["id"]] + [row[field] for field in APARELHO_FIELDS] + [row["created_at"], row["updated_at"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventario.csv"},
    )


@bp.route("/exportar/excel")
def exportar_excel():
    """
    Exporta todo o inventário para um arquivo Excel.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo XLSX para download.
    """
    rows = query_all("SELECT * FROM aparelhos ORDER BY updated_at DESC, id DESC")

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Inventario"
    headers = ["id"] + APARELHO_FIELDS + ["created_at", "updated_at"]
    worksheet.append(headers)

    for row in rows:
        worksheet.append([row["id"]] + [row[field] for field in APARELHO_FIELDS] + [row["created_at"], row["updated_at"]])

    file_stream = io.BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name="inventario_completo.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/<int:aparelho_id>/excluir", methods=["POST"])
def excluir(aparelho_id):
    """
    Exclui um aparelho do inventário.

    Parâmetros:
        aparelho_id (int): identificador do aparelho.

    Retorno:
        Response: redirecionamento para a listagem.
    """
    aparelho = query_one("SELECT linha, imei, usuario FROM aparelhos WHERE id = ?", (aparelho_id,))
    if not aparelho:
        flash("Aparelho não encontrado.", "error")
        return redirect(url_for("inventario.lista"))

    # Remove vínculo de chip antes de excluir
    
    execute("UPDATE chips SET linha = NULL WHERE linha = ?", (aparelho["linha"],))
    execute("DELETE FROM historico_chips WHERE aparelho_id = ?", (aparelho_id,))
    execute("DELETE FROM aparelhos WHERE id = ?", (aparelho_id,))
    log_movement(
        "aparelhos", aparelho_id, "exclusao",
        f"Aparelho excluído: IMEI {aparelho['imei'] or 'N/A'}, usuário {aparelho['usuario'] or 'N/A'}."
    )
    flash("Aparelho excluído com sucesso.", "success")
    return redirect(url_for("inventario.lista"))


@bp.route("/excluir-multiplos", methods=["POST"])
def excluir_multiplos():
    """
    Exclui múltiplos aparelhos em massa.

    Parâmetros:
        Nenhum (recebe lista de IDs via formulário).

    Retorno:
        Response: redirecionamento para a listagem.
    """
    ids = request.form.getlist("ids[]")
    if not ids:
        flash("Nenhum aparelho selecionado.", "warning")
        return redirect(url_for("inventario.lista"))
    count = 0
    for aparelho_id in ids:
        try:
            aparelho = query_one("SELECT imei, linha FROM aparelhos WHERE id = ?", (aparelho_id,))
            if aparelho:
                execute("UPDATE chips SET linha = NULL WHERE linha = ?", (aparelho["linha"],))
                execute("DELETE FROM historico_chips WHERE aparelho_id = ?", (aparelho_id,))
                execute("DELETE FROM aparelhos WHERE id = ?", (aparelho_id,))
                count += 1
        except Exception:
            continue
    flash(f"{count} aparelho(s) excluído(s) com sucesso.", "success")
    return redirect(url_for("inventario.lista"))


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Campos exibidos em tela
# - Novos filtros e exportações
# - Mensagens de feedback ao usuário
#
# Exige cuidado:
# - Lista APARELHO_FIELDS, pois ela precisa permanecer alinhada ao banco
# - Função _sync_chip_with_device, já que afeta integração entre inventário e chips.
