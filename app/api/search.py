from fastapi import APIRouter, Query

from app.core.normalize import normalize_drug_name
from app.core.resolver import DrugResolver
from app.schemas.responses import SearchResponse, SearchResultItem

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    commercialized_only: bool = Query(default=True),
) -> SearchResponse:
    resolver = DrugResolver()
    candidates = resolver.search(q, limit=limit, commercialized_only=commercialized_only)

    return SearchResponse(
        query=q,
        normalized_query=normalize_drug_name(q),
        results=[
            SearchResultItem(
                cis=c.cis,
                canonical_name=c.canonical_name,
                matched_alias=c.matched_alias,
                alias_type=c.alias_type,
                substance_name=c.substance_name,
                score=c.score,
                commercialization_status=c.commercialization_status,
            )
            for c in candidates
        ],
    )
