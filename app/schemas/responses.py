from pydantic import BaseModel

DISCLAIMER = (
    "Correspondance lexicale automatique. Ne constitue pas une validation "
    "médicale ou pharmaceutique."
)


class HealthResponse(BaseModel):
    status: str
    database_loaded: bool
    drug_count: int
    alias_count: int
    database_last_updated: str | None = None


class SearchResultItem(BaseModel):
    cis: str
    canonical_name: str
    matched_alias: str
    alias_type: str
    substance_name: str | None = None
    score: float
    commercialization_status: str | None = None


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResultItem]
    disclaimer: str = DISCLAIMER


class ResolveCandidate(BaseModel):
    cis: str
    canonical_name: str
    matched_alias: str
    substance_name: str | None = None
    score: float
    confidence: str
    evidence: list[str]


class ResolveInput(BaseModel):
    suspected_term: str | None
    normalized_term: str | None


class ResolveResponse(BaseModel):
    input: ResolveInput
    candidates: list[ResolveCandidate]
    disclaimer: str = DISCLAIMER
    notice: str | None = None


class UpdateDatabaseResponse(BaseModel):
    status: str
    drug_count: int
    alias_count: int
    rejected_ratio: float
