import enum

from pydantic import BaseModel, Field


class MatchType(str, enum.Enum):
    """Which half of hybrid retrieval found a result.

    Worth returning rather than hiding: a lexical-only hit is reported with a
    score below the similarity floor, which reads as a bug until you can see it
    was matched on the literal string rather than on meaning.
    """

    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    BOTH = "both"


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int | None = Field(default=None, ge=1, le=50)


class SearchResult(BaseModel):
    document_id: int
    document_title: str
    chunk_id: int
    chunk_index: int
    chunk_text: str
    # Always cosine similarity, for every result however it was found. MySQL's
    # FULLTEXT relevance never reaches the API: it ranks candidates inside the
    # lexical query and is then discarded, because a relevance score and a
    # cosine are different units and combining them would be inventing a number.
    score: float
    match_type: MatchType
