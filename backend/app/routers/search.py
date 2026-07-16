from fastapi import APIRouter, Request

from app.core.deps import CurrentUser, DbSession, get_client_ip
from app.schemas.search import SearchRequest, SearchResult
from app.services import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=list[SearchResult])
def semantic_search(
    payload: SearchRequest, request: Request, db: DbSession, current_user: CurrentUser
) -> list[SearchResult]:
    return search_service.search(
        db,
        query=payload.query,
        k=payload.k,
        user=current_user,
        ip_address=get_client_ip(request),
    )
