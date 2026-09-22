-- Migration: 2026_04_28_refactor.sql
-- Refactor aparelhos table, add data_desligamento, dynamic situacao,
-- and create auxiliary domain tables.

--- 1. Alter aparelhos table ---
ALTER TABLE aparelhos
    DROP COLUMN IF EXISTS imei_mdm,
    DROP COLUMN IF EXISTS modelo_mdm,
    DROP COLUMN IF EXISTS internet,
    DROP COLUMN IF EXISTS grupo,
    DROP COLUMN IF EXISTS conta_google,
    ADD COLUMN IF NOT EXISTS data_desligamento DATE;

--- 2. Trigger/function to keep situacao based on data_desligamento ---
CREATE OR REPLACE FUNCTION update_situacao()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.data_desligamento IS NULL THEN
        NEW.situacao := 'ATIVO';
    ELSE
        NEW.situacao := 'DESLIGADO';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_aparelhos_situacao ON aparelhos;
CREATE TRIGGER trg_aparelhos_situacao
BEFORE INSERT OR UPDATE ON aparelhos
FOR EACH ROW EXECUTE FUNCTION update_situacao();

--- 3. Auxiliary domain tables ---
CREATE TABLE IF NOT EXISTS unidade (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO unidade (nome)
SELECT DISTINCT unidade FROM aparelhos WHERE unidade IS NOT NULL;

CREATE TABLE IF NOT EXISTS estabelecimento (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO estabelecimento (nome)
SELECT DISTINCT estab FROM aparelhos WHERE estab IS NOT NULL;

CREATE TABLE IF NOT EXISTS tipo_linha (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO tipo_linha (nome)
SELECT DISTINCT tipo_linha FROM aparelhos WHERE tipo_linha IS NOT NULL;

CREATE TABLE IF NOT EXISTS status_aparelho (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO status_aparelho (nome)
SELECT DISTINCT status FROM aparelhos WHERE status IS NOT NULL;

CREATE TABLE IF NOT EXISTS uso_aparelho (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO uso_aparelho (nome)
SELECT DISTINCT uso FROM aparelhos WHERE uso IS NOT NULL;

CREATE TABLE IF NOT EXISTS nivel (
    id SERIAL PRIMARY KEY,
    nome TEXT UNIQUE NOT NULL
);
INSERT INTO nivel (nome)
SELECT DISTINCT nivel FROM aparelhos WHERE nivel IS NOT NULL;

-- End of migration