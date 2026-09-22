"""
Arquivo: utils.py
Propósito:
    Funções utilitárias e lógica de negócio compartilhada entre módulos.
"""

from database import execute, query_one


def sync_chip_with_device(aparelho_id, linha, chip, imei):
    """
    Sincroniza os dados de chip informados no aparelho com a tabela de chips.
    Se a linha estiver preenchida, vincula automaticamente ao chip correspondente.

    Parâmetros:
        aparelho_id (int): id do aparelho salvo.
        linha (str | int | None): número da linha do aparelho.
        chip (str | None): ICCID informado.
        imei (str | None): IMEI atual do aparelho.

    Retorno:
        None.
    """
    # Converte linha para str (a coluna no banco é TEXT)
    if linha is not None:
        try:
            linha = str(int(str(linha).strip()))
        except (ValueError, TypeError):
            linha = None

    if not linha and not chip:
        return

    chip_id = None
    chip_iccid = chip

    # Se informou ICCID, busca ou cria o chip por ICCID
    if chip_iccid:
        chip_row = query_one("SELECT id, linha FROM chips WHERE chip = ?", (chip_iccid,))
        if chip_row:
            chip_id = chip_row["id"]
            # Atualiza a linha do chip se fornecida
            if linha:
                execute("UPDATE chips SET linha = ? WHERE id = ?", (linha, chip_id))
        else:
            # Cria novo chip com ICCID e linha informados
            chip_id = execute(
                "INSERT INTO chips (linha, chip, status, observacoes) VALUES (?, ?, ?, ?)",
                (linha, chip_iccid, "ATIVO", "Criado automaticamente ao vincular no inventário."),
            )

    # Se tem linha mas não ICCID, ou para garantir o vínculo por linha
    if linha:
        # Busca chip existente pela linha
        chip_por_linha = query_one(
            "SELECT id, chip FROM chips WHERE linha = ? ORDER BY id DESC LIMIT 1",
            (linha,)
        )
        if chip_por_linha:
            chip_id = chip_por_linha["id"]
            chip_iccid = chip_iccid or chip_por_linha["chip"]
        else:
            # Se não achou chip com essa linha, cria um novo chip só com a linha
            if not chip_id:
                chip_id = execute(
                    "INSERT INTO chips (linha, status, observacoes) VALUES (?, ?, ?)",
                    (linha, "ATIVO", "Criado automaticamente via inventário (linha)."),
                )

    # Registra no histórico se houve algum vínculo
    if chip_id or chip_iccid:
        # Verifica se já existe vínculo recente para evitar duplicatas
        vinculo_existente = query_one(
            "SELECT id FROM historico_chips WHERE aparelho_id = ? AND chip = ? AND linha = ? ORDER BY id DESC LIMIT 1",
            (aparelho_id, chip_iccid, linha),
        )
        if not vinculo_existente:
            execute(
                """
                INSERT INTO historico_chips (chip, aparelho_id, imei, linha, observacao)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chip_iccid, aparelho_id, imei, linha, "Vínculo automático via linha/ICCID."),
            )


def log_movement(entidade, entidade_id, acao, descricao):
    """
    Registra um evento simples no histórico para o dashboard.

    Parâmetros:
        entidade (str): nome lógico da tabela ou área.
        entidade_id (int | None): id relacionado ao evento.
        acao (str): ação executada.
        descricao (str): resumo legível do evento.

    Retorno:
        None.
    """
    execute(
        "INSERT INTO movimentacoes (entidade, entidade_id, acao, descricao) VALUES (?, ?, ?, ?)",
        (entidade, entidade_id, acao, descricao),
    )
