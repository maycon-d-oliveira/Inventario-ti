"""
Arquivo: routes/auth.py
Propósito:
    Gerenciar autenticação de usuários: login, registro e logout.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from forms import LoginForm, RegistrationForm
from database import convert_sql_placeholders, get_db_engine, query_one, execute as execute_sql

bp = Blueprint("auth", __name__)

class User:
    """
    Classe de usuário compatível com Flask-Login.
    """
    def __init__(self, id, username, email, password_hash, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


def load_user(user_id):
    """
    Flask-Login user loader callback.
    """
    if get_db_engine() == "postgres":
        sql = "SELECT id, username, email, password_hash, is_admin FROM usuarios WHERE id = %s"
    else:
        sql = "SELECT id, username, email, password_hash, is_admin FROM usuarios WHERE id = ?"
    row = query_one(sql, (user_id,))
    if row:
        return User(row['id'], row['username'], row['email'], row['password_hash'], bool(row['is_admin']))
    return None


def get_user_by_username(username):
    """
    Busca um usuário pelo username.
    """
    if get_db_engine() == "postgres":
        sql = "SELECT id, username, email, password_hash, is_admin FROM usuarios WHERE username = %s"
    else:
        sql = "SELECT id, username, email, password_hash, is_admin FROM usuarios WHERE username = ?"
    try:
        row = query_one(sql, (username,))
        if row:
            # Simulate a User object; we'll create a simple class later or use a dict
            return {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "password_hash": row["password_hash"],
                "is_admin": row["is_admin"]
            }
        return None
    except Exception as e:
        # If we get an undefined column error for is_admin, try to add the column and retry
        if get_db_engine() == "postgres" and "column \"is_admin\" does not exist" in str(e):
            try:
                # Add the missing column
                if get_db_engine() == "postgres":
                    alter_sql = "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
                else:
                    alter_sql = "ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
                execute_sql(alter_sql)
                # Retry the original query
                row = query_one(sql, (username,))
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "email": row["email"],
                        "password_hash": row["password_hash"],
                        "is_admin": row["is_admin"]
                    }
                return None
            except Exception:
                # If we still fail, re-raise the original exception
                raise e
        else:
            # Re-raise if it's not the expected error
            raise e


def get_user_by_id(user_id):
    """
    Busca um usuário pelo ID.
    """
    if get_db_engine() == "postgres":
        sql = "SELECT id, username, email, password_hash FROM usuarios WHERE id = %s"
    else:
        sql = "SELECT id, username, email, password_hash FROM usuarios WHERE id = ?"
    row = query_one(sql, (user_id,))
    if row:
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "password_hash": row["password_hash"]
        }
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Página de login.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user_data = get_user_by_username(username)
        if user_data and check_password_hash(user_data["password_hash"], password):
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                password_hash=user_data["password_hash"]
            )
            login_user(user, remember=form.remember.data)
            flash("Login realizado com sucesso!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.home"))
        else:
            flash("Login inválido. Verifique usuário e senha.", "error")
    return render_template("auth/login.html", form=form)

@bp.route("/alterar-senha", methods=["GET", "POST"])
@login_required
def alterar_senha():
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "").strip()
        nova_senha = request.form.get("nova_senha", "").strip()
        confirmacao = request.form.get("confirmacao", "").strip()

        # Validações básicas de preenchimento
        if not senha_atual or not nova_senha or not confirmacao:
            flash("Todos os campos são obrigatórios.", "error")
            return render_template("auth/alterar_senha.html")

        # Verifica se a senha atual está correta (current_user usa o método check_password da sua classe User)
        if not current_user.check_password(senha_atual):
            flash("A senha atual informada está incorreta.", "error")
            return render_template("auth/alterar_senha.html")

        # Verifica se a nova senha coincide com a confirmação
        if nova_senha != confirmacao:
            flash("A nova senha e a confirmação não coincidem.", "error")
            return render_template("auth/alterar_senha.html")

        try:
            # Gera o novo hash seguro e atualiza o banco de dados
            novo_hash = generate_password_hash(nova_senha)
            sql = "UPDATE usuarios SET password_hash = %s WHERE id = %s"
            
            execute_sql(convert_sql_placeholders(sql), (novo_hash, current_user.id))
            flash("Sua senha foi alterada com sucesso!", "success")
            return redirect(url_for("dashboard.home"))
            
        except Exception as e:
            flash(f"Erro ao atualizar a senha no banco: {e}", "error")

    # GET: Exibe o formulário de alteração
    return render_template("auth/alterar_senha.html")

@bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Página de registro de novo usuário.
    Se nenhum usuário existir, o primeiro registrado será administrador.
    Caso contrário, apenas administradores podem registrar novos usuários.
    """
    # If user is logged in, check if they are admin (unless we are allowing first user)
    if current_user.is_authenticated:
        # Check if current user is admin
        if not getattr(current_user, 'is_admin', False):
            flash("Apenas administradores podem registrar novos usuários.", "error")
            return redirect(url_for("dashboard.home"))
    else:
        # If not logged in, we allow registration only if there are no users yet.
        # Check if any user exists
        if get_db_engine() == "postgres":
            sql = "SELECT id FROM usuarios LIMIT 1"
        else:
            sql = "SELECT id FROM usuarios LIMIT 1"
        if query_one(sql):
            # There is at least one user, so require login and admin
            flash("Você precisa estar logado como administrador para registrar novos usuários.", "error")
            return redirect(url_for("auth.login"))

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        # Verificar se usuário já existe
        existing = get_user_by_username(username)
        if existing:
            flash("Nome de usuário já existe.", "error")
            return render_template("auth/register.html", form=form)
        
        # Verificar se email já existe
        if get_db_engine() == "postgres":
            sql = "SELECT id FROM usuarios WHERE email = %s"
        else:
            sql = "SELECT id FROM usuarios WHERE email = ?"
        if query_one(sql, (email,)):
            flash("E-mail já cadastrado.", "error")
            return render_template("auth/register.html", form=form)
        
        # Determine if this user should be admin
        if not current_user.is_authenticated:
            # Se for o primeiríssimo usuário criando a conta de fora, vira admin automaticamente
            is_admin = True
        else:
            # Puxa o valor definido no formulário
            is_admin = form.is_admin.data
            
        # Criar novo usuário
        password_hash = generate_password_hash(password)
        if get_db_engine() == "postgres":
            sql = "INSERT INTO usuarios (username, email, password_hash, is_admin) VALUES (%s, %s, %s, %s) RETURNING id"
        else:
            sql = "INSERT INTO usuarios (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)"
        # execute_sql returns lastrowid for SQLite? We'll assume it works.
        user_id = execute_sql(sql, (username, email, password_hash, is_admin))
        if is_admin:
            flash("Primeiro usuário criado com sucesso! Você é um administrador. Faça login.", "success")
        else:
            flash("Registro realizado com sucesso! O usuário pode fazer login agora.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    """
    Logout do usuário.
    """
    logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("auth.login"))