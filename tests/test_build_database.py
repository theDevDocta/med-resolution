from collections import Counter

import pytest

from app.core.config import CONTROL_DRUGS
from app.core.normalize import normalize_drug_name
from app.db.connection import create_connection


def test_build_produces_drugs_and_aliases(built_db_path):
    conn = create_connection(built_db_path, read_only=True)
    try:
        drug_count = conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
        alias_count = conn.execute("SELECT COUNT(*) FROM drug_aliases").fetchone()[0]
    finally:
        conn.close()

    assert drug_count == 6
    assert alias_count > 0


@pytest.mark.parametrize("control_drug", CONTROL_DRUGS)
def test_control_drugs_are_found(built_db_path, control_drug):
    conn = create_connection(built_db_path, read_only=True)
    try:
        normalized = normalize_drug_name(control_drug)
        row = conn.execute(
            "SELECT 1 FROM drug_aliases WHERE alias_normalized LIKE ? LIMIT 1",
            (f"%{normalized}%",),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, f"Médicament de contrôle introuvable : {control_drug}"


def test_aliases_are_deduplicated_per_cis(built_db_path):
    conn = create_connection(built_db_path, read_only=True)
    try:
        rows = conn.execute("SELECT cis, alias_normalized FROM drug_aliases").fetchall()
    finally:
        conn.close()

    per_cis_counts = Counter((row["cis"], row["alias_normalized"]) for row in rows)
    duplicates = [key for key, count in per_cis_counts.items() if count > 1]
    assert duplicates == []


def test_non_commercialized_drug_is_not_excluded(built_db_path):
    conn = create_connection(built_db_path, read_only=True)
    try:
        row = conn.execute(
            "SELECT 1 FROM drug_aliases WHERE alias_normalized LIKE '%lopressor%' LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
