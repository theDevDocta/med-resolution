-- Schéma SQLite du Drug Resolver BDPM. Source de vérité utilisée par
-- l'importeur pour construire la base ; voir app/db/repository.py pour les
-- requêtes.

CREATE TABLE IF NOT EXISTS drugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cis TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    brand_name_normalized TEXT NOT NULL,
    pharmaceutical_form TEXT,
    administration_routes TEXT,
    authorization_status TEXT,
    commercialization_status TEXT,
    holder TEXT
);

CREATE INDEX IF NOT EXISTS idx_drugs_cis ON drugs(cis);
CREATE INDEX IF NOT EXISTS idx_drugs_brand_normalized ON drugs(brand_name_normalized);

CREATE TABLE IF NOT EXISTS substances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cis TEXT NOT NULL,
    substance_code TEXT,
    substance_name TEXT NOT NULL,
    substance_name_normalized TEXT NOT NULL,
    dosage TEXT,
    dosage_unit TEXT
);

CREATE INDEX IF NOT EXISTS idx_substances_cis ON substances(cis);
CREATE INDEX IF NOT EXISTS idx_substances_name_normalized ON substances(substance_name_normalized);

CREATE TABLE IF NOT EXISTS presentations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cis TEXT NOT NULL,
    cip7 TEXT,
    cip13 TEXT,
    presentation_label TEXT,
    presentation_label_normalized TEXT,
    commercialization_status TEXT,
    reimbursement_rate TEXT,
    price TEXT
);

CREATE INDEX IF NOT EXISTS idx_presentations_cis ON presentations(cis);

CREATE TABLE IF NOT EXISTS drug_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cis TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    alias_compact TEXT NOT NULL,
    alias_type TEXT NOT NULL CHECK (alias_type IN ('brand', 'substance', 'presentation', 'generated')),
    canonical_name TEXT NOT NULL,
    substance_name TEXT,
    pharmaceutical_form TEXT,
    dosage TEXT,
    dosage_unit TEXT,
    commercialization_status TEXT
);

CREATE INDEX IF NOT EXISTS idx_aliases_normalized ON drug_aliases(alias_normalized);
CREATE INDEX IF NOT EXISTS idx_aliases_compact ON drug_aliases(alias_compact);
CREATE INDEX IF NOT EXISTS idx_aliases_cis ON drug_aliases(cis);
