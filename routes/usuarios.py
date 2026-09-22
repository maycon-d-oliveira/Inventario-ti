"""
Arquivo: routes/usuarios.py
Propósito:
    Gerenciar usuários do sistema (apenas para administradores).
"""

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import login_required, current_user

from database import execute, query_all, query_one, convert_sql_placeholders
from werkzeug.security import generate_password_hash

bp = Blueprint("usuarios", __name__)


def admin_required():
    """
    Verifica se o usuário atual é um administrador.
    """
    if not current_user.is_authenticated:
        return False
    return getattr(current_user, 'is_admin', False)


@bp.route("/")
@login_required
def lista():
    """
    Lista todos os usuários do sistema com busca e ordenação.
    Apenas administradores podem acessar esta rota.
    """
    if not admin_required():
        flash("Acesso negado. Apenas administradores podem gerenciar usuários.", "error")
        return redirect(url_for("dashboard.home"))

    # Captura parâmetros de filtro e ordenação vindos do front-end
    q = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'username').strip()
    order = request.args.get('order', 'asc').strip()

    # Validação de colunas permitidas para evitar SQL Injection na ordenação
    allowed_sort_cols = ['id', 'username', 'email', 'created_at']
    if sort_by not in allowed_sort_cols:
        sort_by = 'username'
    if order not in ['asc', 'desc']:
        order = 'asc'

    # Construção da Query SQL Dinâmica de busca
    params = []
    sql = "SELECT id, username, email, is_admin, created_at FROM usuarios"
    
    if q:
        sql += " WHERE username LIKE %s OR email LIKE %s"
        params.extend([f"%{q}%", f"%{q}%"])

    sql += f" ORDER BY {sort_by} {order}"

    # Executa a query adaptando os placeholders para o banco ativo
    usuarios = query_all(convert_sql_placeholders(sql), tuple(params))

    return render_template(
        "usuarios/lista.html",
        usuarios=usuarios,
        filters={'q': q},
        sort_by=sort_by,
        order=order
    )

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    """
    Cadastra um novo usuário usando o formulário interno padrão.
    Apenas administradores podem acessar.
    """
    if not admin_required():
        flash("Acesso negado. Apenas administradores podem gerenciar usuários.", "error")
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = True if request.form.get("is_admin") else False

        # Validações básicas
        if not username or not email or not password:
            flash("Todos os campos (incluindo a senha) são obrigatórios.", "error")
            return render_template("usuarios/form.html", usuario=None, is_edit=False)

        try:
            # Verifica se usuário ou e-mail já existem
            engine = get_db_engine() if 'get_db_engine' in globals() else "postgres" # fallback seguro
            
            sql_check = "SELECT id FROM usuarios WHERE username = %s OR email = %s"
            if query_one(convert_sql_placeholders(sql_check), (username, email)):
                flash("Nome de usuário ou E-mail já cadastrado.", "error")
                return render_template("usuarios/form.html", usuario=None, is_edit=False)

            password_hash = generate_password_hash(password)
            
            # Insere no banco
            sql_insert = """
                INSERT INTO usuarios (username, email, password_hash, is_admin)
                VALUES (%s, %s, %s, %s)
            """
            execute(convert_sql_placeholders(sql_insert), (username, email, password_hash, is_admin))
            
            flash(f"Usuário '{username}' cadastrado com sucesso!", "success")
            return redirect(url_for("usuarios.lista"))
            
        except Exception as e:
            flash(f"Erro ao cadastrar usuário: {e}", "error")

    # GET: Renderiza o formulário vazio para criação
    return render_template("usuarios/form.html", usuario=None, is_edit=False)

@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
def editar(usuario_id):
    """
    Edita as informações de um usuário existente e permite alterar permissão de ADM.
    """
    if not admin_required():
        flash("Acesso negado. Apenas administradores podem gerenciar usuários.", "error")
        return redirect(url_for("dashboard.home"))

    sql_select = "SELECT id, username, email, is_admin FROM usuarios WHERE id = %s"
    usuario = query_one(convert_sql_placeholders(sql_select), (usuario_id,))
    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("usuarios.lista"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        # Captura o checkbox de admin (retorna True se estiver marcado, False se ausente)
        is_admin = True if request.form.get("is_admin") else False

        if not username or not email:
            flash("Nome de usuário e E-mail são obrigatórios.", "error")
            return render_template("usuarios/form.html", usuario=usuario, is_edit=True)

        # Prevenir que o administrador logado retire seu próprio privilégio de admin
        if usuario_id == current_user.id and not is_admin:
            flash("Você não pode remover seu próprio acesso de administrador.", "error")
            is_admin = True

        try:
            sql_update = """
                UPDATE usuarios 
                SET username = %s, email = %s, is_admin = %s 
                WHERE id = %s
            """
            execute(convert_sql_placeholders(sql_update), (username, email, is_admin, usuario_id))
            flash(f"Usuário '{username}' atualizado com sucesso.", "success")
            return redirect(url_for("usuarios.lista"))
        except Exception as e:
            flash(f"Erro ao atualizar usuário: {e}", "error")

    return render_template("usuarios/form.html", usuario=usuario, is_edit=True)


@bp.route("/<int:usuario_id>/excluir", methods=["POST"])
@login_required
def excluir(usuario_id):
    """
    Exclui um usuário do sistema.
    """
    if not admin_required():
        flash("Acesso negado. Apenas administradores podem gerenciar usuários.", "error")
        return redirect(url_for("dashboard.home"))

    if usuario_id == current_user.id:
        flash("Você não pode excluir seu próprio usuário enquanto está logado.", "error")
        return redirect(url_for("usuarios.lista"))

    sql_find = "SELECT username FROM usuarios WHERE id = %s"
    usuario = query_one(convert_sql_placeholders(sql_find), (usuario_id,))
    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("usuarios.lista"))

    try:
        sql_delete = "DELETE FROM usuarios WHERE id = %s"
        execute(convert_sql_placeholders(sql_delete), (usuario_id,))
        flash(f"Usuário '{usuario['username']}' excluído com sucesso.", "success")
    except Exception as e:
        flash(f"Erro ao excluir usuário: {e}", "error")

    return redirect(url_for("usuarios.lista"))