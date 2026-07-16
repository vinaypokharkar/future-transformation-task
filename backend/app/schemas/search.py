from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int | None = Field(default=None, ge=1, le=50)


class SearchResult(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    chunk_index: int
    chunk_text: str
    score: float
