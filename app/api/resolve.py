from fastapi import APIRouter

from app.core.resolver import DrugResolver
from app.schemas.requests import ResolveRequest
from app.schemas.responses import ResolveCandidate, ResolveInput, ResolveResponse

router = APIRouter()

NO_RELIABLE_MATCH_NOTICE = "Aucune correspondance fiable trouvée pour ce terme."


@router.post("/resolve", response_model=ResolveResponse)
def resolve(payload: ResolveRequest) -> ResolveResponse:
    resolver = DrugResolver()
    result = resolver.resolve(
        verbatim=payload.verbatim,
        llm_version=payload.llm_version,
        suspected_term=payload.suspected_term,
        context=payload.context,
        limit=payload.limit,
    )

    response = ResolveResponse(
        input=ResolveInput(suspected_term=result.suspected_term, normalized_term=result.normalized_term),
        candidates=[
            ResolveCandidate(
                cis=c.cis,
                canonical_name=c.canonical_name,
                matched_alias=c.matched_alias,
                substance_name=c.substance_name,
                score=c.score,
                confidence=c.confidence,
                evidence=c.evidence,
            )
            for c in result.candidates
        ],
    )

    if not response.candidates or response.candidates[0].score < 55:
        response.notice = NO_RELIABLE_MATCH_NOTICE

    return response
