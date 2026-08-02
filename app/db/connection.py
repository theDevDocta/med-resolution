"""Gestion de la connexion SQLite.

Une connexion en lecture par processus suffit pour ce service (SQLite gère
nativement les lectures concurrentes). Le script de mise à jour construit sa
propre base temporaire avec une connexion séparée (voir importers).
"""

import sqlite3
from pathlib import Path

from app.core.config import DB_PATH


def create_connection(db_path: Path | str = DB_PATH, read_only: bool = False) -> sqlite3.Connection:
    db_path = Path(db_path)
    if read_only:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA query_only = {1 if read_only else 0}")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Connexion partagée utilisée par l'API (paresseuse, réutilisée entre requêtes)."""
    global _connection
    if _connection is None:
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Base BDPM introuvable : {DB_PATH}. Lancez `python -m scripts.update_bdpm`."
            )
        _connection = create_connection(DB_PATH, read_only=True)
    return _connection


def reset_connection() -> None:
    """Ferme la connexion partagée (utile après un remplacement de la base, ou en test)."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
