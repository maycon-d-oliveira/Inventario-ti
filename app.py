"""
Arquivo: app.py
Propósito:
    Inicializar a aplicação Flask, configurar o banco SQLite e registrar
    todos os blueprints de rotas do sistema de inventário de celulares.
"""

import os
from os.path import join, dirname, abspath

from flask import Flask, redirect, url_for, request
from flask_login import LoginManager, current_user

from database import close_db, init_db
from routes import register_blueprints


def create_app():
    """
    Cria e configura a aplicação Flask.

    Parâmetros:
        Nenhum.

    Retorno:
        Flask: instância configurada da aplicação.
    """
    app = Flask(__name__, template_folder='templates')
    # SECRET_KEY deve ser forte e vindo de variável de ambiente em produção
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-USE-STRONG-SECRET")
    app.config["DATABASE"] = "inventario.db"
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL", "").strip()
    app.config["ITEMS_PER_PAGE"] = 50

    # OpenEdge database configuration
    app.config["OPENEDGE_DRIVER"] = os.environ.get(
        "OPENEDGE_DRIVER", "com.ddtek.jdbc.openedge.OpenEdgeDriver"
    )
    app.config["OPENEDGE_JAR"] = os.environ.get("OPENEDGE_JAR", "/home/pi/openedge.jar")
    app.config["OPENEDGE_URL"] = os.environ.get("OPENEDGE_URL", "").strip()
    app.config["OPENEDGE_USER"] = os.environ.get("OPENEDGE_USER", "").strip()
    app.config["OPENEDGE_PASSWORD"] = os.environ.get("OPENEDGE_PASSWORD", "").strip()

    # Registra uma função para fechar a conexão SQLite ao final de cada requisição.
    app.teardown_appcontext(close_db)

    # Filtros customizados do Jinja2
    @app.template_filter('zip')
    def zip_filter(*args):
        """Filtro Jinja2 para zipar múltiplas listas."""
        return list(zip(*args))

    with app.app_context():
        init_db()

    register_blueprints(app)
    # Register custom blueprints
    from routes.pulsus import bp as pulsus_bp
    app.register_blueprint(pulsus_bp)
    # Auth blueprint is already registered via register_blueprints
    from routes.auth import load_user

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"
    login_manager.user_loader(load_user)

   
    
    @app.before_request
    def require_login():
        # List of endpoints that do not require login
        exempt_endpoints = ['auth.login', 'auth.register', 'static']
        if not current_user.is_authenticated:
            if request.endpoint not in exempt_endpoints:
                return redirect(url_for('auth.login'))

    @app.route("/")
    def index():
        """
        Redireciona a raiz do sistema para o dashboard.

        Parâmetros:
            Nenhum.

        Retorno:
            Response: redirecionamento HTTP para a página inicial.
        """
        # url_for monta a URL de uma rota a partir do nome interno do endpoint.
        return redirect(url_for("dashboard.home"))

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    # DEBUG deve ser False em produção - padrão é False para segurança
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - SECRET_KEY em ambiente local ou via variável de ambiente futuramente
# - Configurações simples do Flask
# - Inclusão de novas rotas na função register_blueprints
#
# Exige cuidado:
# - Mudanças no nome do banco ou inicialização do app, pois afetam importação,
#   testes e execução local de toda a aplicação.
