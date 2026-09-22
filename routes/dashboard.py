"""
Arquivo: routes/dashboard.py
Proposito:
    Expor a pagina inicial com indicadores principais, graficos e alertas.
"""

from flask import Blueprint, render_template

from database import get_db_engine, query_all, query_one

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
def home():
    """
    Monta o dashboard principal do sistema.

    Parametros:
        Nenhum.

    Retorno:
        str: HTML renderizado da pagina inicial.
    """
    if get_db_engine() == "postgres":
        movimentacoes_sql = """
            SELECT created_at::date AS dia, COUNT(*) AS total
            FROM movimentacoes
            WHERE created_at >= (CURRENT_DATE - INTERVAL '30 days')
            GROUP BY created_at::date
            ORDER BY dia
        """
        desatualizados_sql = """
            SELECT id, usuario, modelo, updated_at
            FROM aparelhos
            WHERE updated_at < (CURRENT_DATE - INTERVAL '90 days')
               OR updated_at IS NULL
            LIMIT 10
        """
        multiplos_sql = """
            SELECT usuario, COUNT(*) AS qtd, STRING_AGG(modelo, ' | ') AS modelos
            FROM aparelhos
            WHERE UPPER(COALESCE(status, '')) = 'EM USO'
              AND usuario IS NOT NULL
              AND usuario <> ''
            GROUP BY usuario
            HAVING COUNT(*) > 1
            ORDER BY qtd DESC
            LIMIT 10
        """
    else:
        movimentacoes_sql = """
            SELECT date(created_at) AS dia, COUNT(*) AS total
            FROM movimentacoes
            WHERE datetime(created_at) >= datetime('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY dia
        """
        desatualizados_sql = """
            SELECT id, usuario, modelo, updated_at
            FROM aparelhos
            WHERE datetime(updated_at) < datetime('now', '-90 days')
               OR updated_at IS NULL
            LIMIT 10
        """
        multiplos_sql = """
            SELECT usuario, COUNT(*) AS qtd, GROUP_CONCAT(modelo, ' | ') AS modelos
            FROM aparelhos
            WHERE UPPER(COALESCE(status, '')) = 'EM USO'
              AND usuario IS NOT NULL
              AND usuario <> ''
            GROUP BY usuario
            HAVING COUNT(*) > 1
            ORDER BY qtd DESC
            LIMIT 10
        """

    # --- Indicadores principais ---
    totais = {
        "aparelhos_em_uso": query_one(
            "SELECT COUNT(*) AS total FROM aparelhos WHERE UPPER(COALESCE(status, '')) = 'EM USO'"
        )["total"],
        "estoque": query_one("SELECT COUNT(*) AS total FROM estoque")["total"],
        "chips_ativos": query_one(
            "SELECT COUNT(*) AS total FROM chips WHERE LOWER(COALESCE(status, '')) <> 'cancelado'"
        )["total"],
    }

    # --- Dados para graficos (ja existentes) ---
    aparelhos_por_estab = query_all(
        """
        SELECT COALESCE(estab, 'Nao informado') AS estab, COUNT(*) AS total
        FROM aparelhos
        GROUP BY COALESCE(estab, 'Nao informado')
        ORDER BY total DESC, estab
        """
    )

    aparelhos_por_status = [
        {"status": "Em uso", "total": totais["aparelhos_em_uso"]},
        {"status": "Devolvidos", "total": query_one("SELECT COUNT(*) AS total FROM devolvidos")["total"]},
        {"status": "Descarte", "total": query_one("SELECT COUNT(*) AS total FROM descarte")["total"]},
        {"status": "Estoque", "total": totais["estoque"]},
    ]

    # --- Novo: Aparelhos por marca (Top 10) ---
    aparelhos_por_marca = query_all(
        """
        SELECT COALESCE(marca, 'Sem marca') AS marca, COUNT(*) AS total
        FROM aparelhos
        GROUP BY COALESCE(marca, 'Sem marca')
        ORDER BY total DESC
        LIMIT 10
        """
    )

    # --- Novo: Evolucao de movimentacoes (ultimos 30 dias) ---
    movimentacoes_30d = query_all(movimentacoes_sql)

    # Preenche dias sem movimentacao (ultimos 30 dias)
    from datetime import datetime, timedelta
    hoje = datetime.now().date()
    dias_labels = []
    dias_totais = {}
    for item in movimentacoes_30d:
        dia_val = item["dia"]
        if isinstance(dia_val, str):
            dias_totais[dia_val] = item["total"]
        else:
            dias_totais[dia_val.strftime("%Y-%m-%d")] = item["total"]
    for i in range(30):
        dia = (hoje - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        dias_labels.append(dia)
    movimentacoes_labels = [d[5:] for d in dias_labels]  # MM-DD
    movimentacoes_data = [dias_totais.get(d, 0) for d in dias_labels]

    # --- Alertas inteligentes ---
    alertas = []

    # 1. Aparelhos sem IMEI
    sem_imei = query_all(
        "SELECT id, usuario, modelo FROM aparelhos WHERE imei IS NULL OR imei = '' LIMIT 10"
    )
    if sem_imei:
        alertas.append({
            "tipo": "warning",
            "titulo": f"{len(sem_imei)} aparelho(s) sem IMEI cadastrado",
            "itens": sem_imei,
            "link": "/?q=",
            "link_texto": "Ver no inventario",
        })

    # 2. Aparelhos com colaborador desligado ainda em uso
    colab_desligado = query_all(
        """
        SELECT a.id, a.usuario, a.modelo, a.status, c.nome, c.data_desligamento
        FROM aparelhos a
        LEFT JOIN colaboradores c ON UPPER(COALESCE(a.usuario, '')) = UPPER(COALESCE(c.nome, ''))
        WHERE c.data_desligamento IS NOT NULL
          AND UPPER(COALESCE(a.status, '')) = 'EM USO'
        LIMIT 10
        """
    )
    if colab_desligado:
        alertas.append({
            "tipo": "error",
            "titulo": f"{len(colab_desligado)} aparelho(s) com usuario desligado ainda 'EM USO'",
            "itens": colab_desligado,
            "link": "/?q=",
            "link_texto": "Ver no inventario",
        })

    # 3. Chips vazios (sem identificação/número do chip)
    chips_sem_vinculo = query_all(
        """
        SELECT c.id, c.linha, c.chip, c.status
        FROM chips c
        WHERE c.chip IS NULL OR TRIM(c.chip) = ''
        LIMIT 10
        """
    )
    if chips_sem_vinculo:
        alertas.append({
            "tipo": "warning",
            "titulo": f"{len(chips_sem_vinculo)} chip(s) com cadastro vazio/incompleto",
            "itens": chips_sem_vinculo,
            "link": "/chips",
            "link_texto": "Ver chips",
        })

    # 4. Aparelhos desatualizados (mais de 90 dias)
    desatualizados = query_all(desatualizados_sql)
    if desatualizados:
        alertas.append({
            "tipo": "warning",
            "titulo": f"{len(desatualizados)} aparelho(s) sem atualizacao ha mais de 90 dias",
            "itens": desatualizados,
            "link": "/?q=",
            "link_texto": "Ver no inventario",
        })

    # # 5. Colaboradores com multiplos aparelhos em uso
    # multiplos = query_all(multiplos_sql)
    # if multiplos:
    #     alertas.append({
    #         "tipo": "info",
    #         "titulo": f"{len(multiplos)} usuario(s) com multiplos aparelhos em uso",
    #         "itens": multiplos,
    #         "link": "/",
    #         "link_texto": "Ver inventario",
    #     })

    # --- Ultimas movimentacoes ---
    ultimas_atualizacoes = query_all(
        """
        SELECT entidade, acao, descricao, created_at
        FROM movimentacoes
        ORDER BY created_at DESC, id DESC
        LIMIT 10
        """
    )

    return render_template(
        "dashboard.html",
        totais=totais,
        aparelhos_por_estab=aparelhos_por_estab,
        aparelhos_por_status=aparelhos_por_status,
        aparelhos_por_marca=aparelhos_por_marca,
        movimentacoes_labels=movimentacoes_labels,
        movimentacoes_data=movimentacoes_data,
        alertas=alertas,
        ultimas_atualizacoes=ultimas_atualizacoes,
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com seguranca:
# - Novos cards ou consultas do dashboard
#
# Exige cuidado:
# - Consultas muito pesadas, pois o dashboard e a pagina mais acessada.
