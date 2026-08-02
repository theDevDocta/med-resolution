"""Commande de mise à jour de la base BDPM (spec §14).

Télécharge les fichiers BDPM, reconstruit une base SQLite dans un fichier
temporaire, valide le résultat, puis remplace atomiquement la base servie
par l'API. N'écrit jamais directement dans data/bdpm.sqlite pendant la
reconstruction.

Usage : python -m scripts.update_bdpm [--skip-download]
"""

import argparse
import sys

from app.core.config import DB_PATH, RAW_DIR
from app.importers.build_database import ImportValidationError, build_and_replace
from app.importers.download_bdpm import download_bdpm_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Met à jour la base BDPM locale.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Réutilise les fichiers déjà présents dans data/raw/ sans les re-télécharger.",
    )
    args = parser.parse_args()

    if not args.skip_download:
        print("Téléchargement des fichiers BDPM...")
        for path in download_bdpm_files():
            print(f"  {path}")

    print("Construction de la base SQLite...")
    try:
        stats = build_and_replace(RAW_DIR, DB_PATH)
    except ImportValidationError as exc:
        print(f"Import échoué : {exc}", file=sys.stderr)
        return 1

    print(
        f"Base mise à jour : {DB_PATH} "
        f"({stats.drug_count} médicaments, {stats.alias_count} alias, "
        f"{stats.rejected_ratio:.1%} de lignes rejetées)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
