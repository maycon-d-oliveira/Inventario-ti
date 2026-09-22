"""
Arquivo: routes/importacao.py
Proposito:
    Importacao inteligente: upload da planilha, escolha de abas,
    mapeamento de colunas e importacao via interface web.
"""

import json
import os
import tempfile
from datetime import datetime
from io import BytesIO

from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for,
    send_file, jsonify,
)
from flask_login import current_user

from database import execute, query_one, query_all, get_db, convert_sql_placeholders
from importar_planilha import TABLE_COLUMNS
from utils import sync_chip_with_device

# Constantes de validacao
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_ROWS = 5000
REQUIRED_COLUMNS_APARELHOS = {"imei", "linha", "marca", "modelo"}


def get_responsavel_por_cartao(nr_cartao):
    """
    Busca o colaborador pelo número do cartão (matrícula) e retorna o nome do responsável.

    Parâmetros:
        nr_cartao (str | int): número do cartão/matrícula

    Retorno:
        str: nome do responsável ou string vazia se não encontrado
    """
    if not nr_cartao:
        return ""

    try:
        matricula = str(int(str(nr_cartao).strip()))
        colaborador = query_one(
            "SELECT nome FROM colaboradores WHERE matricula = ?",
            (matricula,)
        )
        if colaborador:
            return colaborador["nome"] or ""
    except (ValueError, TypeError):
        pass

    return ""

bp = Blueprint("importacao", __name__)

TABLES_INFO = {
    "aparelhos": "Inventario principal",
    "chips": "Chips",
    "estoque": "Estoque",
    "devolvidos": "Devolvidos",
    "descarte": "Descarte",
    "colaboradores": "Colaboradores",
    "grupos_whatsapp": "Grupos WhatsApp",
    "centros_custo": "Centros de Custo",
}


@bp.route("/", methods=["GET", "POST"])
def importar():
    if request.method == "POST":
        return _upload()
    return render_template("importacao/importar.html")


def _validate_file(arquivo):
    """
    Valida o arquivo antes do processamento.
    Retorna (is_valid, error_message).
    """
    if not arquivo or not arquivo.filename:
        return False, "Nenhum arquivo selecionado."

    # Valida extensão
    ext = arquivo.filename.lower()
    if not ext.endswith(('.xlsx', '.xls')):
        return False, "Formato inválido. Apenas arquivos .xlsx e .xls são aceitos."

    # Valida tamanho
    arquivo.seek(0, 2)  # Vai para o final
    size = arquivo.tell()
    arquivo.seek(0)  # Volta para o início

    if size > MAX_FILE_SIZE_BYTES:
        return False, f"Arquivo muito grande ({size / 1024 / 1024:.1f}MB). Limite máximo: {MAX_FILE_SIZE_MB}MB."

    return True, None


def _generate_template():
    """Gera o template Excel para download."""
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Inventario"

        # Cabeçalhos
        headers = [
            "IMEI", "Linha", "Marca", "Modelo", "Estabelecimento",
            "Tipo Linha", "Status", "Usuário", "Nível"
        ]
        ws.append(headers)

        # Linha de exemplo
        example = [
            "350057714100225", "17996713515", "Samsung", "Galaxy A36", "10",
            "DADOS", "EM USO", "JOAO SILVA", "NIVEL 1"
        ]
        ws.append(example)

        # Salva em memória
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return buffer
    except Exception as e:
        return None


@bp.route("/template")
def download_template():
    """Download do template Excel."""
    buffer = _generate_template()
    if not buffer:
        flash("Erro ao gerar template.", "error")
        return redirect(url_for("importacao.importar"))

    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='modelo_inventario.xlsx'
    )


def _upload():
    if "arquivo" not in request.files:
        flash("Nenhum arquivo enviado.", "error")
        return render_template("importacao/importar.html")

    arquivo = request.files["arquivo"]

    # Validação do arquivo
    is_valid, error_msg = _validate_file(arquivo)
    if not is_valid:
        flash(error_msg, "error")
        return render_template("importacao/importar.html")

    try:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".xlsx", delete=False, dir=os.getcwd(),
        )
        with tmp:
            arquivo.save(tmp)

        # Armazena nome original para log
        session["_import_temp"] = tmp.name
        session["_import_filename"] = arquivo.filename

        return redirect(url_for("importacao.mapear"))
    except Exception as e:
        flash(f"Erro ao salvar arquivo: {e}", "error")
        return render_template("importacao/importar.html")


@bp.route("/mapear", methods=["GET", "POST"])
def mapear():
    temp_path = session.get("_import_temp")
    if not temp_path or not os.path.exists(temp_path):
        flash("Arquivo nao encontrado. Faca o upload novamente.", "error")
        return redirect(url_for("importacao.importar"))

    from openpyxl import load_workbook
    workbook = load_workbook(temp_path, data_only=True)
    sheet_names = workbook.sheetnames

    if request.method == "POST":
        action = request.form.get("action", "preview")
        if action == "import":
            return _processar_mapeamento(workbook)
        else:
            preview_stats = _preview_import(workbook)
            # Armazena erros na sessão para download
            session["_import_errors"] = json.dumps(preview_stats.get("detalhes_erros", []))
            session["_import_preview_stats"] = json.dumps({
                "total_linhas": preview_stats["total_linhas"],
                "inseridas": preview_stats["inseridas"],
                "atualizadas": preview_stats["atualizadas"],
                "ignoradas": preview_stats["ignoradas"]
            })
            return render_template(
                "importacao/preview.html",
                stats=preview_stats,
                sheet_names=sheet_names,
            )

    # Le colunas de cada aba (primeira linha nao vazia)
    sheet_cols = {}
    sheet_preview = {}
    for sn in sheet_names:
        ws = workbook[sn]
        cols = []
        preview_rows = []
        row_iter = ws.iter_rows(values_only=True)
        # Primeira linha = cabecalho
        try:
            first_row = next(row_iter)
            cols = [str(c) if c is not None else f"Col_{i}" for i, c in enumerate(first_row)]
        except StopIteration:
            cols = []

        # Preview: ate 3 linhas de dados
        for i, row in enumerate(row_iter):
            if i >= 3:
                break
            preview_rows.append([str(v) if v is not None else "" for v in row[:len(cols)]])
        sheet_cols[sn] = cols
        sheet_preview[sn] = preview_rows

    # Sugestoes automaticas
    sugestoes = {}
    mapa = {
        "Inventario": "aparelhos",
        "Chips": "chips",
        "Estoque Aparelhos": "estoque",
        "Celulares devolvidos": "devolvidos",
        "Descarte Eletronico": "descarte",
        "VW_COLABORADOR": "colaboradores",
        "Funcionarios": "colaboradores",
        "Grupos WhatsApp": "grupos_whatsapp",
        "CentroCusto": "centros_custo",
    }
    for sn in sheet_names:
        if sn in mapa:
            sugestoes[sn] = mapa[sn]

    return render_template(
        "importacao/mapear.html",
        sheet_names=sheet_names,
        tables_info=TABLES_INFO,
        sugestoes=sugestoes,
        sheet_cols=sheet_cols,
        table_cols=TABLE_COLUMNS,
        sheet_preview=sheet_preview,
    )


def _validate_row(row_dict, table_name):
    """
    Valida uma linha individual antes da importação.
    Retorna (is_valid, error_message).
    """
    errors = []

    if table_name == "aparelhos":
        # IMEI
        imei = row_dict.get("imei", "")
        if imei:
            imei_str = str(imei).strip()
            if not imei_str.isdigit() or len(imei_str) != 15:
                errors.append("IMEI deve ter 15 dígitos")

        # Linha
        linha = row_dict.get("linha", "")
        if linha:
            linha_str = str(linha).replace(" ", "").replace("-", "")
            if not linha_str.isdigit() or len(linha_str) < 10:
                errors.append("Linha telefônica inválida")

        # Marca e Modelo obrigatórios
        if not row_dict.get("marca"):
            errors.append("Marca é obrigatória")
        if not row_dict.get("modelo"):
            errors.append("Modelo é obrigatório")

    return len(errors) == 0, "; ".join(errors)


def _preview_import(workbook):
    """
    Faz o dry-run da importação e retorna estatísticas.
    Retorna dicionário com contagens e erros.
    """
    from importar_planilha import sanitize_value, is_header_like

    preview_stats = {
        "total_linhas": 0,
        "inseridas": 0,
        "atualizadas": 0,
        "ignoradas": 0,
        "erros": [],
        "detalhes_erros": []
    }

    idx = 0
    while True:
        sheet_name = request.form.get(f"sheet_{idx}")
        table_name = request.form.get(f"table_{idx}")
        if sheet_name is None:
            break
        if sheet_name and table_name and table_name in TABLE_COLUMNS:
            if sheet_name not in workbook.sheetnames:
                idx += 1
                continue
            sheet = workbook[sheet_name]

            col_map = {}
            prefix = f"map_{idx}_"
            for key, value in request.form.items():
                if key.startswith(prefix) and value:
                    table_col = key.replace(prefix, "")
                    try:
                        src_idx = int(value)
                        col_map[table_col] = src_idx
                    except ValueError:
                        pass

            columns = TABLE_COLUMNS[table_name]
            string_fields = {"linha", "chip", "imei", "mac_wifi", "serial", "conta_google"}

            row_num = 0
            for raw_row in sheet.iter_rows(values_only=True):
                row_num += 1
                sanitized = [sanitize_value(v) for v in raw_row]

                if all(v is None for v in sanitized):
                    continue
                if is_header_like(sanitized):
                    continue

                row_dict = {}
                for col in columns:
                    if col in col_map:
                        src_idx = col_map[col]
                        if src_idx < len(sanitized):
                            val = sanitized[src_idx]
                            if col in string_fields and val is not None:
                                try:
                                    val = str(int(float(str(val).strip())))
                                except (ValueError, TypeError):
                                    val = None
                            row_dict[col] = val
                        else:
                            row_dict[col] = None

                preview_stats["total_linhas"] += 1

                exists = False
                if table_name == "aparelhos":
                    imei_val = row_dict.get("imei")
                    linha_val = row_dict.get("linha")
                    if imei_val:
                        exists = query_one("SELECT id FROM aparelhos WHERE imei = ?", (imei_val,))
                    elif linha_val:
                        exists = query_one("SELECT id FROM aparelhos WHERE linha = ?", (linha_val,))

                if exists:
                    preview_stats["atualizadas"] += 1
                else:
                    is_valid, error_msg = _validate_row(row_dict, table_name)
                    if is_valid:
                        preview_stats["inseridas"] += 1
                    else:
                        preview_stats["ignoradas"] += 1
                        preview_stats["detalhes_erros"].append({
                            "num_linha": row_num,
                            "aba": sheet_name,
                            "erro": error_msg,
                            "imei": row_dict.get("imei", ""),
                            "telefone": row_dict.get("linha", "")
                        })

        idx += 1

    return preview_stats


def _importar_sheet_tx(db, sheet, table_name, col_map, debug=False, log=None):
    """Importa uma aba usando o mapeamento de colunas dentro de uma transação."""
    import sys
    from importar_planilha import sanitize_value, is_header_like

    if log is None:
        log = {"total": 0, "inseridas": 0, "atualizadas": 0, "ignoradas": 0, "erros_detalhes": []}

    columns = TABLE_COLUMNS[table_name]
    integer_fields = {"mdm_id", "nr_cartao"}
    string_fields = {"linha", "chip", "imei", "mac_wifi", "serial", "conta_google"}
    rows_to_insert = []

    prefix = f"[IMPORT][{sheet.title}->{table_name}]"
    if debug:
        print(f"{prefix} TABLE_COLUMNS for {table_name} = {columns}", file=sys.stderr)
        print(f"{prefix} === INICIANDO IMPORTACAO (TX) ===", file=sys.stderr)

    row_count = 0
    for raw_row in sheet.iter_rows(values_only=True):
        row_count += 1
        try:
            sanitized = [sanitize_value(v) for v in raw_row]

            if all(v is None for v in sanitized):
                continue
            if is_header_like(sanitized):
                continue

            if table_name == "grupos_whatsapp":
                for idx in [3, 5]:
                    if idx < len(sanitized) and isinstance(sanitized[idx], str):
                        val = sanitized[idx].strip().lower()
                        sanitized[idx] = 1 if val in {"sim", "true", "1", "x"} else 0

            row_dict = {}
            mapped = []
            if col_map:
                for col in columns:
                    if col in col_map:
                        src_idx = col_map[col]
                        if src_idx < len(sanitized):
                            val = sanitized[src_idx]
                            if col in integer_fields and val is not None:
                                try:
                                    val = int(val)
                                except (ValueError, TypeError):
                                    val = None
                            elif col in string_fields and val is not None:
                                try:
                                    val = str(int(float(str(val).strip())))
                                except (ValueError, TypeError):
                                    val = None
                            mapped.append(val)
                        else:
                            mapped.append(None)
                    else:
                        mapped.append(None)
                if any(v is not None for v in mapped):
                    row_dict = dict(zip(columns, mapped))
            else:
                row_values = sanitized[:len(columns)]
                for i, col in enumerate(columns):
                    if i < len(row_values):
                        val = row_values[i]
                        if col in integer_fields and val is not None:
                            try:
                                row_values[i] = int(val)
                            except (ValueError, TypeError):
                                row_values[i] = None
                        elif col in string_fields and val is not None:
                            try:
                                row_values[i] = str(int(float(str(val).strip())))
                            except (ValueError, TypeError):
                                row_values[i] = None
                mapped = row_values
                row_dict = dict(zip(columns, row_values)) if len(row_values) == len(columns) else {}

            log["total"] += 1

            # Verificar duplicata
            exists = False
            if table_name == "aparelhos":
                imei_val = row_dict.get("imei")
                linha_val = row_dict.get("linha")
                if imei_val:
                    result = db.execute("SELECT id FROM aparelhos WHERE imei = %s", (imei_val,)).fetchone()
                    exists = result is not None
                elif linha_val:
                    result = db.execute("SELECT id FROM aparelhos WHERE linha = %s", (linha_val,)).fetchone()
                    exists = result is not None

            if exists:
                log["atualizadas"] += 1
            else:
                is_valid, error_msg = _validate_row(row_dict, table_name)
                if is_valid:
                    log["inseridas"] += 1
                    rows_to_insert.append(tuple(mapped))
                else:
                    log["ignoradas"] += 1
                    log["erros_detalhes"].append({
                        "num_linha": row_count,
                        "aba": sheet.title,
                        "erro": error_msg,
                        "imei": row_dict.get("imei", ""),
                        "telefone": row_dict.get("linha", "")
                    })

        except Exception as e:
            print(f"{prefix} ERRO: {str(e)}", file=sys.stderr)
            continue

    if not rows_to_insert:
        return 0

    # PostgreSQL uses %s placeholders
    placeholders = ", ".join(["%s"] * len(columns))
    columns_sql = ", ".join(columns)
    sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"

    if debug:
        print(f"{prefix} SQL={sql}", file=sys.stderr)

    count = 0
    for i, row in enumerate(rows_to_insert):
        try:
            db.execute(sql, tuple(row))
            count += 1
        except Exception as e:
            print(f"{prefix} ERRO AO INSERIR linha {i+2}: SQL={sql}, params={tuple(row)}, error={str(e)}", file=sys.stderr)
            continue

    return count


def _processar_mapeamento(workbook):
    """Processa o mapeamento e importa com transação completa."""
    import sys
    import json
    total = 0
    import_log = {
        "total": 0,
        "inseridas": 0,
        "atualizadas": 0,
        "ignoradas": 0,
        "erros_detalhes": []
    }
    log_prefix = "[PROCESSAR_MAPEAMENTO]"

    filename = session.get("_import_filename", "desconhecido")
    username = current_user.username if current_user and current_user.is_authenticated else "anon"

    try:
        db = get_db()

        # Formato esperado:
        #   sheet_X: nome da aba
        #   table_X: tabela destino
        #   map_X_Y: onde X=índice, Y=nome_coluna_tabela, valor=índice_coluna_aba
        tables_to_clear = []
        sheet_map_list = []

        idx = 0
        while True:
            sheet_name = request.form.get(f"sheet_{idx}")
            table_name = request.form.get(f"table_{idx}")
            if sheet_name is None:
                break
            if sheet_name and table_name and table_name in TABLE_COLUMNS:
                if sheet_name in workbook.sheetnames:
                    col_map = {}
                    prefix = f"map_{idx}_"
                    for key, value in request.form.items():
                        if key.startswith(prefix) and value:
                            table_col = key.replace(prefix, "")
                            try:
                                src_idx = int(value)
                                col_map[table_col] = src_idx
                            except ValueError:
                                pass

                    sheet_map_list.append({
                        "sheet": workbook[sheet_name],
                        "table_name": table_name,
                        "col_map": col_map
                    })
                    if table_name not in tables_to_clear:
                        tables_to_clear.append(table_name)
            idx += 1

        # Inicia transação
        try:
            for table_name in tables_to_clear:
                db.execute(f"DELETE FROM {table_name}")
            db.commit()

            # Importa cada aba dentro da mesma transação
            for sheet_data in sheet_map_list:
                sheet = sheet_data["sheet"]
                table_name = sheet_data["table_name"]
                col_map = sheet_data["col_map"]

                count = _importar_sheet_tx(db, sheet, table_name, col_map, debug=True, log=import_log)
                total += count

            # Salva log de importação e armazena erros na sessão
            log_json = json.dumps(import_log.get("erros_detalhes", []))
            session["_import_errors"] = log_json
            db.execute(
                "INSERT INTO log_importacao (usuario, nome_arquivo, total_linhas, inseridas, atualizadas, ignoradas, detalhes_erros) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (username, filename, import_log["total"], import_log["inseridas"],
                 import_log["atualizadas"], import_log["ignoradas"], log_json)
            )
            db.commit()

        except Exception as tx_error:
            # Rollback completo
            db.rollback()
            print(f"{log_prefix} ERRO TRANSACIONAL: {str(tx_error)}", file=sys.stderr)
            flash(f"Erro durante a importação. Nenhuma linha foi salva: {str(tx_error)}", "error")
            return redirect(url_for("importacao.importar"))

        temp_path = session.pop("_import_temp", None)
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

        flash(f"Importacao concluida: {total} registros importados.", "success")

    except Exception as e:
        print(f"{log_prefix} ERRO GERAL: {str(e)}", file=sys.stderr)
        flash(f"Erro inesperado: {str(e)}", "error")

    return redirect(url_for("importacao.importar"))


def _generate_error_report_xlsx(errors_list):
    """
    Gera um arquivo Excel com as linhas que tiveram erro.
    """
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Erros"

        # Cabeçalhos
        ws.append(["Linha", "Aba", "Erro", "IMEI", "Telefone"])

        for erro in errors_list:
            ws.append([
                erro.get("num_linha", ""),
                erro.get("aba", ""),
                erro.get("erro", ""),
                erro.get("imei", ""),
                erro.get("telefone", "")
            ])

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Erro ao gerar relatório Excel: {e}", file=__import__('sys').stderr)
        return None


@bp.route("/erros")
def download_erros():
    """Download do relatório de erros em Excel."""
    errors_json = session.get("_import_errors")
    if not errors_json:
        flash("Nenhum erro disponível para download.", "error")
        return redirect(url_for("importacao.importar"))

    try:
        errors_list = json.loads(errors_json)
    except (json.JSONDecodeError, TypeError):
        flash("Erro ao ler os dados de erros.", "error")
        return redirect(url_for("importacao.importar"))

    buffer = _generate_error_report_xlsx(errors_list)
    if not buffer:
        flash("Erro ao gerar relatório Excel.", "error")
        return redirect(url_for("importacao.importar"))

    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='erros_importacao.xlsx'
    )


@bp.route("/historico")
def historico():
    """Exibe histórico de importações."""
    logs = query_all("""
        SELECT id, usuario, nome_arquivo, total_linhas, inseridas, atualizadas,
               ignoradas, created_at
        FROM log_importacao
        ORDER BY created_at DESC
        LIMIT 50
    """) or []

    return render_template("importacao/historico.html", logs=logs)