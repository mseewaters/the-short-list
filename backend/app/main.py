from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.category_intelligence.llm import CategoryIntelligenceError, get_llm_config_metadata
from app.category_intelligence.extraction import extract_category
from app.category_intelligence.service import get_category_intelligence
from app.graph import compiled_graph
from app.schemas import (
    CategoryExtractRequest,
    CategoryExtractResponse,
    CategoryIntelligenceRequest,
    CategoryIntelligenceResponse,
    ClarifyRequest,
    ClarifyResponse,
    CriterionResult,
    CreateSessionRequest,
    ProductCandidate,
    Requirement,
    SearchRequest,
    SearchResponse,
    SessionResponse,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


sessions: dict[str, dict] = {}


def criteria_for_product(product: dict, requirements: list[dict]) -> list[CriterionResult]:
    criteria = []
    product_results = product["criteria_results"]

    for requirement in requirements:
        label = requirement["label"]
        result = product_results.get(
            label,
            {
                "met": True,
                "note": f"Mock result for {requirement['value']}.",
            },
        )
        criteria.append(
            CriterionResult(
                label=label,
                met=result["met"],
                note=result["note"],
            )
        )

    return criteria


def mock_ceiling_fans(requirements: list[dict]) -> list[ProductCandidate]:
    products = [
        {
            "id": "fan_001",
            "name": "Harbor Breeze Mazon 44-in Low Profile",
            "price": "$179",
            "score": 92,
            "verdict": "Best match",
            "criteria_results": {
                "Room": {"met": True, "note": "Compact bedroom-friendly size."},
                "Priority: Quiet operation": {"met": True, "note": "Mock result: quiet DC-style operation."},
                "Priority: Low profile": {"met": True, "note": "Flush-mount profile works with an 8-foot ceiling."},
                "Priority: Attractive design": {"met": True, "note": "Simple, non-builder-grade look."},
                "Budget": {"met": True, "note": "Under the stated budget."},
                "Ceiling height": {"met": True, "note": "Low-profile fit for 8-foot ceilings."},
            },
        },
        {
            "id": "fan_002",
            "name": "Hunter Dempsey 44-in Low Profile",
            "price": "$249",
            "score": 86,
            "verdict": "Good match",
            "criteria_results": {
                "Room": {"met": True, "note": "Appropriate for bedroom use."},
                "Priority: Quiet operation": {"met": True, "note": "Mock result: quiet enough for a bedroom."},
                "Priority: Low profile": {"met": True, "note": "Designed as a low-profile fan."},
                "Priority: Attractive design": {"met": True, "note": "Cleaner style than a basic builder fan."},
                "Budget": {"met": True, "note": "Within the stated budget."},
                "Ceiling height": {"met": True, "note": "Works for an 8-foot ceiling."},
            },
        },
        {
            "id": "fan_003",
            "name": "Hampton Bay Hugger 52-in",
            "price": "$119",
            "score": 71,
            "verdict": "Budget fallback",
            "criteria_results": {
                "Room": {"met": True, "note": "Could work, but may be large depending on room dimensions."},
                "Priority: Quiet operation": {"met": False, "note": "Mock result: less confidence for quiet bedroom use."},
                "Priority: Low profile": {"met": True, "note": "Hugger mount fits lower ceilings."},
                "Priority: Attractive design": {"met": False, "note": "More builder-grade than the other options."},
                "Budget": {"met": True, "note": "Lowest mock price."},
                "Ceiling height": {"met": True, "note": "Hugger style works for 8-foot ceilings."},
            },
        },
    ]

    return [
        ProductCandidate(
            id=product["id"],
            name=product["name"],
            price=product["price"],
            score=product["score"],
            verdict=product["verdict"],
            criteria=criteria_for_product(product, requirements),
        )
        for product in products
    ]


def mock_products(products: list[dict], requirements: list[dict]) -> list[ProductCandidate]:
    return [
        ProductCandidate(
            id=product["id"],
            name=product["name"],
            price=product["price"],
            score=product["score"],
            verdict=product["verdict"],
            criteria=criteria_for_product(product, requirements),
        )
        for product in products
    ]


def mock_robot_vacuums(requirements: list[dict]) -> list[ProductCandidate]:
    return mock_products(
        [
            {
                "id": "vac_001",
                "name": "Roomba Combo j7+",
                "price": "$499",
                "score": 91,
                "verdict": "Best match",
                "criteria_results": {
                    "User context": {"met": True, "note": "Self-emptying base reduces bending and maintenance."},
                    "Priority: Easy maintenance": {"met": True, "note": "Designed around automated emptying."},
                    "Priority: Pet hair handling": {"met": True, "note": "Mock result: strong fit for homes with dogs."},
                    "Priority: Simple controls": {"met": True, "note": "Can run on a schedule after setup."},
                },
            },
            {
                "id": "vac_002",
                "name": "Shark AI Ultra Self-Empty",
                "price": "$399",
                "score": 86,
                "verdict": "Good match",
                "criteria_results": {
                    "User context": {"met": True, "note": "Self-empty base helps older users."},
                    "Priority: Easy maintenance": {"met": True, "note": "Lower-touch than manual-bin options."},
                    "Priority: Pet hair handling": {"met": True, "note": "Mock result: good pet hair fit."},
                    "Priority: Simple controls": {"met": False, "note": "App setup may be less friendly."},
                },
            },
            {
                "id": "vac_003",
                "name": "Eufy RoboVac 11S Max",
                "price": "$249",
                "score": 68,
                "verdict": "Budget fallback",
                "criteria_results": {
                    "User context": {"met": False, "note": "Manual emptying is less ideal for elderly parents."},
                    "Priority: Easy maintenance": {"met": False, "note": "No self-emptying base."},
                    "Priority: Pet hair handling": {"met": True, "note": "Mock result: acceptable for light pet hair."},
                    "Priority: Simple controls": {"met": True, "note": "Remote-style operation is simple."},
                },
            },
        ],
        requirements,
    )


def mock_tvs(requirements: list[dict]) -> list[ProductCandidate]:
    return mock_products(
        [
            {
                "id": "tv_001",
                "name": "Samsung QN90C Neo QLED",
                "price": "$1,199",
                "score": 93,
                "verdict": "Best match",
                "criteria_results": {
                    "Room": {"met": True, "note": "Strong mock fit for bright rooms."},
                    "Priority: High brightness": {"met": True, "note": "Very bright panel class."},
                    "Priority: Anti-glare screen": {"met": True, "note": "Better glare handling than basic TVs."},
                },
            },
            {
                "id": "tv_002",
                "name": "Sony X90L Full Array LED",
                "price": "$999",
                "score": 84,
                "verdict": "Good match",
                "criteria_results": {
                    "Room": {"met": True, "note": "Good bright-room fallback."},
                    "Priority: High brightness": {"met": True, "note": "Bright enough for many daylight rooms."},
                    "Priority: Anti-glare screen": {"met": False, "note": "Mock result: glare handling is less strong."},
                },
            },
            {
                "id": "tv_003",
                "name": "LG C3 OLED",
                "price": "$1,299",
                "score": 72,
                "verdict": "Not ideal",
                "criteria_results": {
                    "Room": {"met": False, "note": "OLED is less ideal for very bright rooms."},
                    "Priority: High brightness": {"met": False, "note": "Not the strongest mock brightness fit."},
                    "Priority: Anti-glare screen": {"met": True, "note": "Good picture, but room brightness is the concern."},
                },
            },
        ],
        requirements,
    )


def mock_coffee_makers(requirements: list[dict]) -> list[ProductCandidate]:
    return mock_products(
        [
            {
                "id": "coffee_001",
                "name": "Keurig K-Mini Plus",
                "price": "$109",
                "score": 90,
                "verdict": "Best match",
                "criteria_results": {
                    "User context": {"met": True, "note": "Single-serve design fits one person."},
                    "Priority: Fast brewing": {"met": True, "note": "Quick cup before leaving."},
                    "Priority: Small footprint": {"met": True, "note": "Narrow counter footprint."},
                },
            },
            {
                "id": "coffee_002",
                "name": "Ninja Pods and Grounds Specialty Single-Serve",
                "price": "$149",
                "score": 84,
                "verdict": "Good match",
                "criteria_results": {
                    "User context": {"met": True, "note": "Flexible single-cup use."},
                    "Priority: Fast brewing": {"met": True, "note": "Good for quick mornings."},
                    "Priority: Small footprint": {"met": False, "note": "Larger than the smallest options."},
                },
            },
            {
                "id": "coffee_003",
                "name": "Mr. Coffee 5-Cup Mini Brew",
                "price": "$35",
                "score": 70,
                "verdict": "Budget fallback",
                "criteria_results": {
                    "User context": {"met": True, "note": "Small batch works for one person."},
                    "Priority: Fast brewing": {"met": False, "note": "Less grab-and-go than pod options."},
                    "Priority: Small footprint": {"met": True, "note": "Compact and inexpensive."},
                },
            },
        ],
        requirements,
    )


def mock_routers(requirements: list[dict]) -> list[ProductCandidate]:
    return mock_products(
        [
            {
                "id": "router_001",
                "name": "Eero 6+ Mesh 3-Pack",
                "price": "$299",
                "score": 92,
                "verdict": "Best match",
                "criteria_results": {
                    "Home layout": {"met": True, "note": "Mesh nodes are a strong fit for 3 stories."},
                    "Priority: Whole-home coverage": {"met": True, "note": "Designed to spread coverage across floors."},
                    "Priority: Strong signal": {"met": True, "note": "Better fit than a single router."},
                },
            },
            {
                "id": "router_002",
                "name": "TP-Link Deco X55 3-Pack",
                "price": "$249",
                "score": 88,
                "verdict": "Good match",
                "criteria_results": {
                    "Home layout": {"met": True, "note": "Mesh layout works for multiple floors."},
                    "Priority: Whole-home coverage": {"met": True, "note": "Good mock coverage fit."},
                    "Priority: Strong signal": {"met": True, "note": "Strong value option."},
                },
            },
            {
                "id": "router_003",
                "name": "Netgear Nighthawk AX5400",
                "price": "$199",
                "score": 69,
                "verdict": "Partial match",
                "criteria_results": {
                    "Home layout": {"met": False, "note": "Single router may struggle across 3 stories."},
                    "Priority: Whole-home coverage": {"met": False, "note": "Mesh is safer for this layout."},
                    "Priority: Strong signal": {"met": True, "note": "Strong single-router signal, but placement matters."},
                },
            },
        ],
        requirements,
    )


@app.get("/")
def root():
    return {"message": "the-short-list backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/llm-config")
def llm_config():
    return get_llm_config_metadata()


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

    previous_intent = session.get("search_intent") or {}

    graph_state = compiled_graph.invoke(
        {
            "user_message": request.message,
            "category": previous_intent.get("category_label") or request.category,
            "raw_requirements": previous_intent.get("raw_requirements", {}),
            "missing_fields": previous_intent.get("missing_fields", []),
            "agent_message": "Got it. I will turn that into requirements next.",
            "ready_to_search": False,
            "agent_trace": [],
        }
    )

    requirements = [
        Requirement(
            label=key,
            value=value,
        )
        for key, value in graph_state.get("raw_requirements", {}).items()
    ]

    search_intent = {
        "id": f"intent_{request.session_id}",
        "category_label": graph_state.get("category"),
        "category_confidence": "high" if graph_state.get("category") else "low",
        "raw_requirements": graph_state.get("raw_requirements", {}),
        "requirements": [requirement.model_dump() for requirement in requirements],
        "constraints": [],
        "missing_fields": graph_state.get("missing_fields", []),
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
        category=graph_state.get("category"),
        requirements=requirements,
        missing_fields=graph_state.get("missing_fields", []),
        agent_trace=graph_state.get("agent_trace", []),
        agent_message=agent_message,
        ready_to_search=graph_state.get("ready_to_search", False),
    )


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    session = sessions.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    search_intent = session.get("search_intent")
    if search_intent is None:
        raise HTTPException(status_code=400, detail="Clarify before searching")

    category = search_intent.get("category_label")
    requirements = search_intent.get("requirements", [])

    if category == "Ceiling fan":
        candidates = mock_ceiling_fans(requirements)
        recommendation = (
            "Best mock recommendation: Harbor Breeze Mazon 44-in Low Profile. "
            "It is the strongest fit for quiet, low-profile, non-builder-grade bedroom use "
            "while staying under the stated budget."
        )
    elif category == "Robot vacuum":
        candidates = mock_robot_vacuums(requirements)
        recommendation = (
            "Best mock recommendation: Roomba Combo j7+. It best fits elderly parents with two dogs "
            "because the self-emptying base reduces maintenance and the mock scoring favors pet hair handling."
        )
    elif category == "TV":
        candidates = mock_tvs(requirements)
        recommendation = (
            "Best mock recommendation: Samsung QN90C Neo QLED. It is the strongest fit for a bright room "
            "because the mock scoring prioritizes brightness and glare handling."
        )
    elif category == "Coffee maker":
        candidates = mock_coffee_makers(requirements)
        recommendation = (
            "Best mock recommendation: Keurig K-Mini Plus. It best fits a single person on the go "
            "because it is quick, simple, and compact."
        )
    elif category == "Router":
        candidates = mock_routers(requirements)
        recommendation = (
            "Best mock recommendation: Eero 6+ Mesh 3-Pack. It best fits a 3-story house because "
            "mesh coverage is safer than relying on one strong router."
        )
    else:
        candidates = []
        recommendation = "Mock search supports ceiling fans, robot vacuums, TVs, coffee makers, and routers right now."

    return SearchResponse(
        status="complete",
        candidates=candidates,
        recommendation=recommendation,
    )


@app.post("/api/category-intelligence", response_model=CategoryIntelligenceResponse)
def category_intelligence(request: CategoryIntelligenceRequest):
    try:
        record, cached = get_category_intelligence(
            category=request.category,
            context=request.context,
        )
    except CategoryIntelligenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CategoryIntelligenceResponse(
        category=record.category,
        raw_intelligence=record.raw_intelligence.model_dump(),
        normalized_intelligence=record.normalized_intelligence.model_dump(by_alias=True),
        cached=cached,
    )


@app.post("/api/category-extract", response_model=CategoryExtractResponse)
def category_extract(request: CategoryExtractRequest):
    try:
        return CategoryExtractResponse(**extract_category(request.user_input, request.additional_context))
    except CategoryIntelligenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
