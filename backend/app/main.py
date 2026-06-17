from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.graph import compiled_graph
from app.schemas import ClarifyRequest, ClarifyResponse, CreateSessionRequest, SessionResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


sessions: dict[str, dict] = {}


def missing_information_question(field: str) -> str:
    questions = {
        "product category": "What kind of product are you trying to choose?",
        "what matters most": "What are one or two things that matter most for this decision?",
    }

    return questions.get(field, f"What is the {field}?")


@app.get("/")
def root():
    return {"message": "the-short-list backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionResponse)
def create_session(request: CreateSessionRequest):
    session_id = f"sess_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    sessions[session_id] = {
        "session_id": session_id,
        "user_id": request.user_id,
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "search_intent": None,
    }

    return SessionResponse(
        session_id=session_id,
        messages=sessions[session_id]["messages"],
        search_intent=sessions[session_id]["search_intent"],
    )


@app.post("/clarify", response_model=ClarifyResponse)
def clarify(request: ClarifyRequest):
    session = sessions.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc).isoformat()
    session["updated_at"] = now
    session["messages"].append(
        {
            "role": "user",
            "text": request.message,
            "timestamp": now,
        }
    )

    graph_state = compiled_graph.invoke(
        {
            "user_message": request.message,
            "category": None,
            "raw_requirements": {},
            "missing_fields": [],
            "agent_message": "Got it. I will turn that into requirements next.",
            "ready_to_search": False,
            "activity_events": [],
        }
    )

    search_intent = {
        "id": f"intent_{request.session_id}",
        "category_label": graph_state.get("category"),
        "category_confidence": "high" if graph_state.get("category") else "low",
        "raw_requirements": graph_state.get("raw_requirements", {}),
        "requirements": [
            {
                "id": f"req_{index:03}",
                "label": key.replace("_", " ").title(),
                "user_language": request.message,
                "interpreted_need": value,
                "priority": "should_have",
                "confidence": "medium",
                "derived_from_message_ids": [],
            }
            for index, (key, value) in enumerate(
                graph_state.get("raw_requirements", {}).items(),
                start=1,
            )
        ],
        "constraints": [],
        "missing_information": [
            {
                "field": field,
                "reason": "Needed before product research.",
                "question": missing_information_question(field),
                "required_before_search": True,
            }
            for field in graph_state.get("missing_fields", [])
        ],
        "ready_to_search": graph_state.get("ready_to_search", False),
    }

    agent_message = graph_state.get("agent_message", "")
    session["search_intent"] = search_intent
    session["messages"].append(
        {
            "role": "agent",
            "text": agent_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    return ClarifyResponse(
        agent_message=agent_message,
        search_intent=search_intent,
        ready_to_search=graph_state.get("ready_to_search", False),
        activity_events=graph_state.get("activity_events", []),
    )
