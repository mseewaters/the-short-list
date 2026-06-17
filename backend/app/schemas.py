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


class ClarifyResponse(BaseModel):
    status: str = "ok"
    agent_message: str
    search_intent: dict
    ready_to_search: bool
    activity_events: list[dict] = Field(default_factory=list)
