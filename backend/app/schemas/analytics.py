from pydantic import BaseModel


class TaskAnalytics(BaseModel):
    """Task-level: completed means every assignee has finished."""

    total: int
    completed: int
    pending: int
    completion_rate: float


class AssignmentAnalytics(BaseModel):
    """Per-person: how much of the assigned work is done.

    Separate from TaskAnalytics because the two answer different questions. A
    task assigned to three people with two finished is 0 tasks completed but 2
    assignments completed — reporting only one of those misrepresents the other.
    """

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
    assignments: AssignmentAnalytics
    documents: DocumentAnalytics
    search: SearchAnalytics
    activity: ActivityAnalytics
