"""
Arquivo: routes/manutencao.py
Propósito:
    Gerenciar todas as operações de manutenção de aparelhos.
    Segue o fluxo: ENVIAR PARA MANUTENÇÃO → AGUARDANDO ORÇAMENTO → AGUARDANDO APROVAÇÃO → APROVADO/RECUSADO/GARANTIA
"""

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)
from flask_login import login_required, current_user
from database import execute, query_all, query_one

bp = Blueprint("manutencao", __name__)


@bp.route("/")
@login_required
def lista():
    """Lista todas as manutenções com filtros."""
    # Obter parâmetros de filtro
    status_filter = request.args.get("status", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")
    estab_filter = request.args.get("estab", "")

    # Construir query base
    query = """
        SELECT m.*, a.usuario, a.modelo, a.marca, a.imei,
               e.descricao as unidade_descricao
        FROM manutencoes m
        LEFT JOIN aparelhos a ON m.aparelho_id = a.id
        LEFT JOIN estabelecimentos e ON m.estab = e.codigo
        WHERE 1=1
    """
    params = []

    # Aplicar filtros
    if status_filter:
        query += " AND m.status = ?"
        params.append(status_filter)

    if data_inicio:
        query += " AND m.data_envio >= ?"
        params.append(data_inicio)

    if data_fim:
        query += " AND m.data_envio <= ?"
        params.append(data_fim)

    if estab_filter:
        query += " AND m.estab = ?"
        params.append(estab_filter)

    query += " ORDER BY m.data_envio DESC NULLS LAST, m.created_at DESC"

    manutencoes = query_all(query, tuple(params) if params else ())

    # Obter estatísticas
    stats = {
        "total": len(manutencoes),
        "enviar_manutencao": len([m for m in manutencoes if m["status"] == "ENVIAR PARA MANUTENÇÃO"]),
        "aguardando_orcamento": len([m for m in manutencoes if m["status"] == "AGUARDANDO ORÇAMENTO"]),
        "aguardando_aprovacao": len([m for m in manutencoes if m["status"] == "AGUARDANDO APROVAÇÃO"]),
        "aprovado": len([m for m in manutencoes if m["status"] == "APROVADO"]),
        "recusado": len([m for m in manutencoes if m["status"] == "RECUSADO"]),
        "garantia": len([m for m in manutencoes if m["status"] == "GARANTIA"]),
    }

    # Obter lista de empresas suporte
    empresas = query_all("SELECT descricao FROM empresas_suporte ORDER BY descricao")

    # Obter lista de estabelecimentos para filtro
    estabelecimentos = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo")

    return render_template(
        "manutencao/index.html",
        manutencoes=manutencoes,
        stats=stats,
        empresas_suporte=[e["descricao"] for e in empresas],
        estabelecimentos=estabelecimentos,
        estab_filter=estab_filter,
        status_filter=status_filter,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status_options=[
            ("ENVIAR PARA MANUTENÇÃO", "ENVIAR PARA MANUTENÇÃO"),
            ("AGUARDANDO ORÇAMENTO", "AGUARDANDO ORÇAMENTO"),
            ("AGUARDANDO APROVAÇÃO", "AGUARDANDO APROVAÇÃO"),
            ("APROVADO", "APROVADO"),
            ("RECUSADO", "RECUSADO"),
            ("GARANTIA", "GARANTIA"),
        ]
    )


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    """Formulário para nova manutenção (manual)."""
    if request.method == "POST":
        # Gerar código único
        codigo = _gerar_codigo_manutencao()

        # Obter dados do formulário
        data = {
            "codigo": codigo,
            "aparelho_id": request.form.get("aparelho_id"),
            "problema_reportado": request.form.get("problema_reportado"),
            "usuario": request.form.get("usuario"),
            "centro_custo": request.form.get("centro_custo"),
            "aprovador": request.form.get("aprovador"),
            "estab": request.form.get("estab"),
            "unidade": request.form.get("unidade"),
            "empresa_suporte": request.form.get("empresa_suporte"),
            "numero_chamado": request.form.get("numero_chamado"),
            "observacoes": request.form.get("observacoes"),
            "status": "ENVIAR PARA MANUTENÇÃO",
        }

        # Se aparelho_id informado, buscar dados do aparelho
        if data["aparelho_id"]:
            aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (data["aparelho_id"],))
            if aparelho:
                data["id_pulsus"] = aparelho["mdm_id"]
                data["imei"] = aparelho["imei"]
                data["marca"] = aparelho["marca"]
                data["modelo"] = aparelho["modelo"]

        # Inserir no banco
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())

        try:
            execute(
                f"INSERT INTO manutencoes ({columns}) VALUES ({placeholders})",
                values
            )

            # Se aparelho informado, atualizar status
            if data["aparelho_id"]:
                execute(
                    "UPDATE aparelhos SET status = 'EM MANUTENÇÃO' WHERE id = ?",
                    (data["aparelho_id"],)
                )
                # Registrar movimentação
                execute(
                    "INSERT INTO movimentacoes (entidade, entidade_id, acao, descricao) VALUES (?, ?, ?, ?)",
                    ("aparelhos", data["aparelho_id"], "manutencao", f"Aparelho enviado para manutenção (código {codigo})")
                )

            flash("Manutenção registrada com sucesso.", "success")
            return redirect(url_for("manutencao.lista"))

        except Exception as e:
            flash(f"Erro ao registrar manutenção: {e}", "error")

    # Buscar dados para formulário
    aparelhos = query_all("SELECT id, mdm_id, imei, modelo, marca FROM aparelhos ORDER BY modelo")
    estabelecimentos = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo")
    empresas = query_all("SELECT descricao FROM empresas_suporte ORDER BY descricao")

    return render_template(
        "manutencao/form.html",
        aparelhos=aparelhos,
        estabelecimentos=estabelecimentos,
        empresas_suporte=empresas,
        manutencao=None
    )


@bp.route("/nova/<int:aparelho_id>", methods=["GET", "POST"])
@login_required
def nova_para_aparelho(aparelho_id):
    """Formulário para nova manutenção pré-preenchido a partir do inventário."""
    # Buscar dados do aparelho
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (aparelho_id,))
    if not aparelho:
        flash("Aparelho não encontrado.", "error")
        return redirect(url_for("inventario.lista"))

    # GET: Mostra formulário pré-preenchido
    if request.method == "GET":
        aparelhos = query_all("SELECT id, mdm_id, imei, modelo, marca FROM aparelhos ORDER BY modelo")
        estabelecimentos = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo")
        unidades = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY descricao")
        empresas = query_all("SELECT descricao FROM empresas_suporte ORDER BY descricao")

        return render_template(
            "manutencao/form.html",
            aparelho=aparelho,
            aparelhos=aparelhos,
            estabelecimentos=estabelecimentos,
            unidades=unidades,
            empresas_suporte=empresas,
            manutencao=None,
            preenchido=True
        )

    # POST: Salva a manutenção
    if request.method == "POST":
        # Gerar código único
        codigo = _gerar_codigo_manutencao()

        # Obter dados do formulário
        data = {
            "codigo": codigo,
            "aparelho_id": aparelho_id,
            "id_pulsus": aparelho["mdm_id"],
            "imei": aparelho["imei"],
            "marca": aparelho["marca"],
            "modelo": aparelho["modelo"],
            "problema_reportado": request.form.get("problema_reportado"),
            "usuario": request.form.get("usuario"),
            "centro_custo": request.form.get("centro_custo"),
            "aprovador": request.form.get("aprovador"),
            "estab": aparelho["estab"],
            "unidade": request.form.get("unidade"),
            "empresa_suporte": request.form.get("empresa_suporte"),
            "numero_chamado": request.form.get("numero_chamado"),
            "observacoes": request.form.get("observacoes"),
            "status": "ENVIAR PARA MANUTENÇÃO",
        }

        # Inserir no banco
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())

        try:
            execute(
                f"INSERT INTO manutencoes ({columns}) VALUES ({placeholders})",
                values
            )

            # Atualizar status do aparelho
            execute(
                "UPDATE aparelhos SET status = 'EM MANUTENÇÃO' WHERE id = ?",
                (aparelho_id,)
            )

            # Registrar movimentação
            execute(
                "INSERT INTO movimentacoes (entidade, entidade_id, acao, descricao) VALUES (?, ?, ?, ?)",
                ("aparelhos", aparelho_id, "manutencao", f"Aparelho enviado para manutenção (código {codigo})")
            )

            flash("Manutenção registrada com sucesso.", "success")
            return redirect(url_for("manutencao.lista"))

        except Exception as e:
            flash(f"Erro ao registrar manutenção: {e}", "error")

    # Buscar dados adicionais para formulário (GET)
    aparelhos = query_all("SELECT id, mdm_id, imei, modelo, marca FROM aparelhos ORDER BY modelo")
    estabelecimentos = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo")
    unidades = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY descricao")
    empresas = query_all("SELECT descricao FROM empresas_suporte ORDER BY descricao")

    return render_template(
        "manutencao/form.html",
        aparelho=aparelho,
        aparelhos=aparelhos,
        estabelecimentos=estabelecimentos,
        unidades=unidades,
        empresas_suporte=empresas,
        manutencao=None,
        preenchido=True
    )


@bp.route("/<int:id>", methods=["GET"])
@login_required
def detalhe(id):
    """Detalhe da manutenção."""
    manutencao = query_one("""
        SELECT m.*, a.usuario, a.modelo, a.marca, a.imei,
               e.descricao as unidade_descricao
        FROM manutencoes m
        LEFT JOIN aparelhos a ON m.aparelho_id = a.id
        LEFT JOIN estabelecimentos e ON m.estab = e.codigo
        WHERE m.id = ?
    """, (id,))

    if not manutencao:
        flash("Manutenção não encontrada.", "error")
        return redirect(url_for("manutencao.lista"))

    # Buscar histórico de status
    historico = query_all("""
        SELECT id, status, created_at as data_alteracao
        FROM manutencoes
        WHERE id = ?
        ORDER BY created_at DESC
    """, (id,))

    return render_template(
        "manutencao/detalhe.html",
        manutencao=manutencao,
        historico=historico
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    """Editar registro de manutenção."""
    manutencao = query_one("""
        SELECT m.*, a.usuario, a.modelo, a.marca, a.imei,
               e.descricao as unidade_descricao
        FROM manutencoes m
        LEFT JOIN aparelhos a ON m.aparelho_id = a.id
        LEFT JOIN estabelecimentos e ON m.estab = e.codigo
        WHERE m.id = ?
    """, (id,))

    if not manutencao:
        flash("Manutenção não encontrada.", "error")
        return redirect(url_for("manutencao.lista"))

    if request.method == "POST":
        # Obter dados do formulário
        data = {
            "problema_reportado": request.form.get("problema_reportado"),
            "usuario": request.form.get("usuario"),
            "centro_custo": request.form.get("centro_custo"),
            "aprovador": request.form.get("aprovador"),
            "estab": request.form.get("estab"),
            "empresa_suporte": request.form.get("empresa_suporte"),
            "data_envio": request.form.get("data_envio"),
            "nf_envio": request.form.get("nf_envio"),
            "descricao_manutencao": request.form.get("descricao_manutencao"),
            "orcamento": request.form.get("orcamento"),
            "valor_final": request.form.get("valor_final"),
            "numero_pedido": request.form.get("numero_pedido"),
            "numero_chamado": request.form.get("numero_chamado"),
            "data_retorno": request.form.get("data_retorno"),
            "observacoes": request.form.get("observacoes"),
        }

        # Atualizar no banco
        updates = []
        values = []
        for key, value in data.items():
            if value is not None and value != "":
                updates.append(f"{key} = ?")
                values.append(value)
        values.append(id)

        if updates:
            try:
                execute(
                    f"UPDATE manutencoes SET {', '.join(updates)} WHERE id = ?",
                    values
                )

                # Verificar se precisa avançar status
                _avancar_status_automatico(id)

                flash("Manutenção atualizada com sucesso.", "success")
            except Exception as e:
                flash(f"Erro ao atualizar manutenção: {e}", "error")

        return redirect(url_for("manutencao.detalhe", id=id))

    # Buscar dados adicionais para formulário
    aparelhos = query_all("SELECT id, mdm_id, imei, modelo, marca FROM aparelhos ORDER BY modelo")
    estabelecimentos = query_all("SELECT codigo, descricao FROM estabelecimentos ORDER BY codigo")

    # Se houver aparelho associado, buscar seus dados detalhados
    aparelho_detalhado = None
    if manutencao.get("aparelho_id"):
        aparelho_detalhado = query_one("""
            SELECT a.*, e.descricao as unidade_descricao
            FROM aparelhos a
            LEFT JOIN estabelecimentos e ON a.estab = e.codigo
            WHERE a.id = ?
        """, (manutencao["aparelho_id"],))

    empresas = query_all("SELECT descricao FROM empresas_suporte ORDER BY descricao")

    return render_template(
        "manutencao/form.html",
        aparelho=aparelho_detalhado or manutencao,
        aparelhos=aparelhos,
        estabelecimentos=estabelecimentos,
        unidades=estabelecimentos,  # Unidades são os mesmos estabelecimentos
        empresas_suporte=empresas,
        manutencao=manutencao,
        editar=True
    )


@bp.route("/<int:id>/status", methods=["POST"])
@login_required
def atualizar_status(id):
    """Atualizar status manual da manutenção."""
    novo_status = request.form.get("status")

    if not novo_status:
        flash("Status não informado", "error")
        return redirect(url_for("manutencao.lista"))

    # Validar status
    status_validos = ["ENVIAR PARA MANUTENÇÃO", "AGUARDANDO ORÇAMENTO", "AGUARDANDO APROVAÇÃO", "APROVADO", "RECUSADO", "GARANTIA"]
    if novo_status not in status_validos:
        flash("Status inválido", "error")
        return redirect(url_for("manutencao.lista"))

    try:
        # Atualizar status
        execute(
            "UPDATE manutencoes SET status = ? WHERE id = ?",
            (novo_status, id)
        )

        # Verificar se precisa atualizar o aparelho (se tem data_retorno preenchida)
        _avancar_status_automatico(id)

        flash("Status atualizado com sucesso", "success")

    except Exception as e:
        flash(f"Erro ao atualizar status: {e}", "error")

    return redirect(url_for("manutencao.lista"))


@bp.route("/<int:id>/historico", methods=["GET"])
@login_required
def historico_aparelho(id):
    """Histórico de manutenções do aparelho."""
    # Buscar aparelho
    aparelho = query_one("SELECT * FROM aparelhos WHERE id = ?", (id,))
    if not aparelho:
        flash("Aparelho não encontrado.", "error")
        return redirect(url_for("inventario.lista"))

    # Buscar histórico de manutenções
    historico = query_all("""
        SELECT m.*, e.descricao as unidade_descricao
        FROM manutencoes m
        LEFT JOIN estabelecimentos e ON m.estab = e.codigo
        WHERE m.aparelho_id = ?
        ORDER BY m.created_at DESC
    """, (id,))

    return render_template(
        "manutencao/historico.html",
        aparelho=aparelho,
        historico=historico
    )


def _gerar_codigo_manutencao():
    """Gera um código sequencial para manutenção."""
    # Buscar o último código utilizado
    ultimo = query_one("SELECT MAX(codigo) as ultimo FROM manutencoes")
    if ultimo and ultimo["ultimo"]:
        codigo = ultimo["ultimo"] + 1
    else:
        codigo = 1
    return codigo


def _avancar_status_automatico(manutencao_id):
    """Avança status automaticamente com base nos campos preenchidos."""
    manutencao = query_one("SELECT * FROM manutencoes WHERE id = ?", (manutencao_id,))
    if not manutencao:
        return

    # Sempre que data_retorno for preenchida, atualizar status do aparelho para Disponível
    # independentemente do status da manutenção
    if manutencao["data_retorno"] and manutencao["aparelho_id"]:
        execute("UPDATE aparelhos SET status = 'Disponível' WHERE id = ?", (manutencao["aparelho_id"],))

        # Verificar se já existe movimentação de retorno para não duplicar
        movimento_existe = query_one(
            "SELECT id FROM movimentacoes WHERE entidade = 'aparelhos' AND entidade_id = ? AND acao = 'manutencao_concluida'",
            (manutencao["aparelho_id"],)
        )
        if not movimento_existe:
            execute(
                "INSERT INTO movimentacoes (entidade, entidade_id, acao, descricao) VALUES (?, ?, ?, ?)",
                ("aparelhos", manutencao["aparelho_id"], "manutencao_concluida", f"Aparelho retornou da manutenção (código {manutencao['codigo']})")
            )

    status_atual = manutencao["status"]

    # Regras de avanço de status
    if status_atual == "ENVIAR PARA MANUTENÇÃO" and manutencao["data_envio"] and manutencao["nf_envio"]:
        # Avança para AGUARDANDO ORÇAMENTO
        execute("UPDATE manutencoes SET status = 'AGUARDANDO ORÇAMENTO' WHERE id = ?", (manutencao_id,))

    elif status_atual == "AGUARDANDO ORÇAMENTO" and manutencao["descricao_manutencao"] and manutencao["orcamento"] and manutencao["numero_pedido"]:
        # Avança para AGUARDANDO APROVAÇÃO
        execute("UPDATE manutencoes SET status = 'AGUARDANDO APROVAÇÃO' WHERE id = ?", (manutencao_id,))