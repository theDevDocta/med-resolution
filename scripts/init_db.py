"""Crée une base SQLite vide (schéma seul), utile pour les tests ou un premier démarrage."""

from app.core.config import DB_PATH
from app.db.connection import create_connection, init_schema


def main() -> None:
    conn = create_connection(DB_PATH)
    init_schema(conn)
    conn.close()
    print(f"Schéma initialisé : {DB_PATH}")


if __name__ == "__main__":
    main()
