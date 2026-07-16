from pydantic import BaseModel


class TaskAnalytics(BaseModel):
    total: int
    completed: int
    pending: int
    completion_rate: float


class DocumentAnalytics(BaseModel):
    total: int
    indexed: int
    total_chunks: int


class TopQuery(BaseModel):
    query: str
    count: int


class SearchAnalytics(BaseModel):
    total_searches: int
    top_queries: list[TopQuery]


class ActivityAnalytics(BaseModel):
    logins_last_7_days: int


class AnalyticsOut(BaseModel):
    tasks: TaskAnalytics
    documents: DocumentAnalytics
    search: SearchAnalytics
    activity: ActivityAnalytics
