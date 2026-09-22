"""
Arquivo: migrate_add_columns.py
Proposito: Adicionar colunas faltantes nas tabelas aparelhos e usuarios do PostgreSQL.
Execute: py migrate_add_columns.py
"""
import os
import psycopg2

# Configuracoes do PostgreSQL (mesmas do app.py)
DB_URL = os.environ.get(
    "DATABASE_URL",
    "host=172.0.0.217 port=5432 dbname=hcm user=sysprogress password=sysprogress"
)

# Columns to add for aparelhos table
APARELHOS_COLUMNS_TO_ADD = [
    ("internet", "TEXT"),
    ("grupo", "TEXT"),
    ("modelo_mdm", "TEXT"),
    ("imei_mdm", "TEXT"),
    ("conta_google", "TEXT"),
]

# Columns to add for usuarios table
USUARIOS_COLUMNS_TO_ADD = [
    ("is_admin", "BOOLEAN NOT NULL DEFAULT FALSE"),
]

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Add columns to aparelhos
    for col_name, col_type in APARELHOS_COLUMNS_TO_ADD:
        try:
            cur.execute(f'ALTER TABLE aparelhos ADD COLUMN IF NOT EXISTS {col_name} {col_type};')
            print(f"Coluna '{col_name}' adicionada ou ja existente na tabela aparelhos.")
        except Exception as e:
            print(f"Erro ao adicionar '{col_name}' na tabela aparelhos: {e}")

    # Add columns to usuarios
    for col_name, col_type in USUARIOS_COLUMNS_TO_ADD:
        try:
            cur.execute(f'ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS {col_name} {col_type};')
            print(f"Coluna '{col_name}' adicionada ou ja existente na tabela usuarios.")
        except Exception as e:
            print(f"Erro ao adicionar '{col_name}' na tabela usuarios: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("Migracao concluida.")

if __name__ == "__main__":
    main()
