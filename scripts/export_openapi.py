"""Exporte le schéma OpenAPI de l'API vers openapi.json (génération de client).

Usage : python -m scripts.export_openapi [chemin_sortie]
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> int:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    output_path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"Schéma OpenAPI écrit dans {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
