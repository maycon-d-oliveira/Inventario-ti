"""
Arquivo: routes/grupos.py
Propósito:
    Listar grupos de WhatsApp e seus integrantes corporativos.
"""

import csv
import io

from flask import Blueprint, Response, render_template

from database import query_all

bp = Blueprint("grupos", __name__)


@bp.route("/")
def lista():
    """
    Lista grupos e integrantes cadastrados.

    Parâmetros:
        Nenhum.

    Retorno:
        str: HTML da tela de grupos.
    """
    grupos = query_all(
        """
        SELECT grupo,
               COUNT(*) AS total_integrantes,
               SUM(CASE WHEN linha_corporativa = 1 THEN 1 ELSE 0 END) AS linhas_corporativas
        FROM grupos_whatsapp
        GROUP BY grupo
        ORDER BY grupo
        """
    )
    integrantes = query_all("SELECT * FROM grupos_whatsapp ORDER BY grupo, nome_integrante")
    return render_template("grupos/lista.html", grupos=grupos, integrantes=integrantes)


@bp.route("/exportar/csv")
def exportar_csv():
    """
    Exporta a base de grupos de WhatsApp para CSV.

    Parâmetros:
        Nenhum.

    Retorno:
        Response: arquivo CSV para download.
    """
    rows = query_all("SELECT * FROM grupos_whatsapp ORDER BY grupo, nome_integrante")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "grupo",
            "linha",
            "nome_integrante",
            "administrador",
            "unidade",
            "linha_corporativa",
            "responsavel_informar",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["grupo"],
                row["linha"],
                row["nome_integrante"],
                row["administrador"],
                row["unidade"],
                row["linha_corporativa"],
                row["responsavel_informar"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=grupos_whatsapp.csv"},
    )


# === COMO MANTER ESTE ARQUIVO ===
# Pode alterar com segurança:
# - Agregações da tela de grupos
# - Colunas exibidas na tabela de integrantes
#
# Exige cuidado:
# - Se futuramente houver relacionamento forte entre grupos e linhas, reavalie
#   a modelagem antes de mudar a forma de consulta.
