"""
Arquivo: routes/__init__.py
Propósito:
    Reunir e registrar todos os blueprints do sistema Flask.
"""

from routes.chips import bp as chips_bp
from routes.colaboradores import bp as colaboradores_bp
from routes.dashboard import bp as dashboard_bp
from routes.descarte import bp as descarte_bp
from routes.devolvidos import bp as devolvidos_bp
from routes.estoque import bp as estoque_bp
from routes.grupos import bp as grupos_bp
from routes.inventario import bp as inventario_bp
from routes.auxiliares import bp as auxiliares_bp
from routes.importacao import bp as importacao_bp
from routes.auth import bp as auth_bp
from routes.usuarios import bp as usuarios_bp
from routes.manutencao import bp as manutencao_bp


def register_blueprints(app):
    """
    Registra os blueprints da aplicação Flask.

    Parâmetros:
        app (Flask): instância principal da aplicação.

    Retorno:
        None.
    """
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventario_bp, url_prefix="/inventario")
    app.register_blueprint(chips_bp, url_prefix="/chips")
    app.register_blueprint(estoque_bp, url_prefix="/estoque")
    app.register_blueprint(devolvidos_bp, url_prefix="/devolvidos")
    app.register_blueprint(descarte_bp, url_prefix="/descarte")
    app.register_blueprint(colaboradores_bp, url_prefix="/colaboradores")
    app.register_blueprint(grupos_bp, url_prefix="/grupos")
    app.register_blueprint(importacao_bp, url_prefix='/importacao')
    app.register_blueprint(auxiliares_bp, url_prefix='/auxiliares')
    app.register_blueprint(manutencao_bp, url_prefix='/manutencao')  # Manutenção blueprint
    app.register_blueprint(auth_bp)  # Auth blueprint (no url_prefix, it will be at /login, /register, /logout)
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')  # Usuarios blueprint (admin only)


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Registro de novos blueprints
#
# Exige cuidado:
# - Mudanças nos prefixos de URL, pois links e bookmarks podem depender deles.
