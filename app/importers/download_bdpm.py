"""Téléchargement des fichiers plats BDPM vers data/raw/."""

import httpx

from app.core.config import BDPM_FILES, RAW_DIR

TIMEOUT_SECONDS = 30.0


def download_bdpm_files() -> list[str]:
    """Télécharge chaque fichier listé dans BDPM_FILES vers RAW_DIR.

    Retourne la liste des chemins de fichiers téléchargés.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []

    with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
        for filename, url in BDPM_FILES.items():
            response = client.get(url)
            response.raise_for_status()
            destination = RAW_DIR / filename
            destination.write_bytes(response.content)
            downloaded.append(str(destination))

    return downloaded


if __name__ == "__main__":
    for path in download_bdpm_files():
        print(f"Téléchargé : {path}")
