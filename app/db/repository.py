"""Accès aux données : insertion (import) et recherche (résolution).

Toute la logique SQL est centralisée ici pour que les autres modules
(importers, resolver) n'écrivent jamais de requêtes directement.
"""

import sqlite3

from app.core.config import SQL_PRESELECTION_LIMIT
from app.db.models import DrugAlias


def insert_drugs(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO drugs (
            cis, brand_name, brand_name_normalized, pharmaceutical_form,
            administration_routes, authorization_status,
            commercialization_status, holder
        ) VALUES (:cis, :brand_name, :brand_name_normalized, :pharmaceutical_form,
                   :administration_routes, :authorization_status,
                   :commercialization_status, :holder)
        """,
        rows,
    )


def insert_substances(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO substances (
            cis, substance_code, substance_name, substance_name_normalized,
            dosage, dosage_unit
        ) VALUES (:cis, :substance_code, :substance_name, :substance_name_normalized,
                   :dosage, :dosage_unit)
        """,
        rows,
    )


def insert_presentations(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO presentations (
            cis, cip7, cip13, presentation_label, presentation_label_normalized,
            commercialization_status, reimbursement_rate, price
        ) VALUES (:cis, :cip7, :cip13, :presentation_label, :presentation_label_normalized,
                   :commercialization_status, :reimbursement_rate, :price)
        """,
        rows,
    )


def insert_aliases(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """
        INSERT INTO drug_aliases (
            cis, alias, alias_normalized, alias_compact, alias_type,
            canonical_name, substance_name, pharmaceutical_form, dosage,
            dosage_unit, commercialization_status
        ) VALUES (:cis, :alias, :alias_normalized, :alias_compact, :alias_type,
                   :canonical_name, :substance_name, :pharmaceutical_form, :dosage,
                   :dosage_unit, :commercialization_status)
        """,
        rows,
    )


def count_drugs(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(DISTINCT cis) FROM drugs").fetchone()[0]


def count_aliases(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM drug_aliases").fetchone()[0]


def preselect_aliases(
    conn: sqlite3.Connection,
    normalized_query: str,
    compact_query: str,
    limit: int = SQL_PRESELECTION_LIMIT,
) -> list[DrugAlias]:
    """Présélection SQL (spec §10, étape 1) : correspondance exacte, préfixe,
    sous-chaîne, ou forme compacte. Le classement fin est fait ensuite par
    RapidFuzz (voir app/core/resolver.py)."""
    if not normalized_query:
        return []

    prefix = f"{normalized_query}%"
    substring = f"%{normalized_query}%"
    compact_prefix = f"{compact_query}%"

    rows = conn.execute(
        """
        SELECT * FROM drug_aliases
        WHERE alias_normalized = :exact
           OR alias_normalized LIKE :prefix
           OR alias_normalized LIKE :substring
           OR alias_compact LIKE :compact_prefix
        ORDER BY
            CASE WHEN alias_normalized = :exact THEN 0
                 WHEN alias_normalized LIKE :prefix THEN 1
                 ELSE 2
            END
        LIMIT :limit
        """,
        {
            "exact": normalized_query,
            "prefix": prefix,
            "substring": substring,
            "compact_prefix": compact_prefix,
            "limit": limit,
        },
    ).fetchall()

    if len(rows) < 20 and normalized_query:
        # Filet de sécurité : première lettre + longueur approximative,
        # pour ne pas rater un candidat trop éloigné du préfixe exact (faute
        # au milieu du mot). Trié par proximité de longueur pour que les
        # candidats les plus plausibles survivent à la limite même sur une
        # base volumineuse (où la première lettre seule est peu sélective).
        first_letter = normalized_query[0]
        query_len = len(normalized_query)
        approx_len_low = max(1, query_len - 3)
        approx_len_high = query_len + 3
        fallback_limit = max(limit, 1000)
        fallback_rows = conn.execute(
            """
            SELECT * FROM drug_aliases
            WHERE alias_normalized LIKE :letter_prefix
              AND LENGTH(alias_normalized) BETWEEN :len_low AND :len_high
            ORDER BY ABS(LENGTH(alias_normalized) - :query_len) ASC
            LIMIT :limit
            """,
            {
                "letter_prefix": f"{first_letter}%",
                "len_low": approx_len_low,
                "len_high": approx_len_high,
                "query_len": query_len,
                "limit": fallback_limit,
            },
        ).fetchall()
        seen_ids = {row["id"] for row in rows}
        rows = list(rows) + [r for r in fallback_rows if r["id"] not in seen_ids]

    return [DrugAlias.from_row(row) for row in rows]


def get_drug_by_cis(conn: sqlite3.Connection, cis: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM drugs WHERE cis = ? LIMIT 1", (cis,)).fetchone()
