from pydantic import BaseModel, Field


class ResolveRequest(BaseModel):
    verbatim: str = Field(..., min_length=1)
    llm_version: str | None = None
    suspected_term: str | None = None
    context: str | None = None
    limit: int = Field(default=5, ge=1, le=50)
