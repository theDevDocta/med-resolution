from datetime import datetime, timezone

from fastapi import APIRouter

from app.core import config
from app.db import repository
from app.db.connection import get_connection
from app.schemas.responses import HealthResponse

router = APIRouter()


def _database_last_updated() -> str | None:
    try:
        mtime = config.DB_PATH.stat().st_mtime
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        conn = get_connection()
        drug_count = repository.count_drugs(conn)
        alias_count = repository.count_aliases(conn)
        return HealthResponse(
            status="ok",
            database_loaded=True,
            drug_count=drug_count,
            alias_count=alias_count,
            database_last_updated=_database_last_updated(),
        )
    except FileNotFoundError:
        return HealthResponse(status="degraded", database_loaded=False, drug_count=0, alias_count=0)
