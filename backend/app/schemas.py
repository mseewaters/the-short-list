from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    user_id: str = "default"


class SessionResponse(BaseModel):
    status: str = "ok"
    session_id: str
    user_context: dict | None = None
    messages: list[dict] = Field(default_factory=list)
    search_intent: dict | None = None


class ClarifyRequest(BaseModel):
    session_id: str
    user_id: str = "default"
    message: str


class Requirement(BaseModel):
    label: str
    value: str


class ClarifyResponse(BaseModel):
    category: str | None
    requirements: list[Requirement] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    agent_trace: list[str] = Field(default_factory=list)
    agent_message: str
    ready_to_search: bool


class SearchRequest(BaseModel):
    session_id: str


class CriterionResult(BaseModel):
    label: str
    met: bool
    note: str


class ProductCandidate(BaseModel):
    id: str
    name: str
    price: str
    score: int
    verdict: str
    criteria: list[CriterionResult] = Field(default_factory=list)


class SearchResponse(BaseModel):
    status: str
    candidates: list[ProductCandidate] = Field(default_factory=list)
    recommendation: str
