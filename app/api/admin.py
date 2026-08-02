"""Route d'administration : mise à jour de la base BDPM à chaud (sans redémarrer le service).

Réutilise le même chemin que `scripts/update_bdpm.py` (téléchargement +
reconstruction + remplacement atomique), puis invalide la connexion SQLite
partagée pour que les requêtes suivantes lisent la nouvelle base.
"""

import threading

import httpx
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core import config
from app.db.connection import reset_connection
from app.importers.build_database import ImportValidationError, build_and_replace
from app.importers.download_bdpm import download_bdpm_files
from app.schemas.responses import UpdateDatabaseResponse

router = APIRouter()

# Une seule reconstruction à la fois : télécharger/écraser data/raw/ en
# parallèle corromprait l'import en cours.
_update_lock = threading.Lock()

_admin_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="AdminKeyAuth", auto_error=False)


def verify_admin_key(x_admin_key: str | None = Security(_admin_key_header)) -> None:
    """Vérifie X-Admin-Key contre ADMIN_API_KEY si celle-ci est configurée."""
    if config.ADMIN_API_KEY and x_admin_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé d'administration invalide ou manquante.")


@router.post(
    "/admin/update-database",
    response_model=UpdateDatabaseResponse,
    dependencies=[Depends(verify_admin_key)],
)
def update_database(skip_download: bool = False) -> UpdateDatabaseResponse:
    if not _update_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Une mise à jour de la base est déjà en cours.")
    try:
        if not skip_download:
            try:
                download_bdpm_files()
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail=f"Téléchargement BDPM échoué : {exc}") from exc

        try:
            stats = build_and_replace(config.RAW_DIR, config.DB_PATH)
        except ImportValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        reset_connection()
        return UpdateDatabaseResponse(
            status="ok",
            drug_count=stats.drug_count,
            alias_count=stats.alias_count,
            rejected_ratio=stats.rejected_ratio,
        )
    finally:
        _update_lock.release()
