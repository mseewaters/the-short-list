"""Search router: POST /search.

Runs a mock product search against the session's accumulated requirements and
returns ranked product candidates with per-criterion results.

Mock data covers: ceiling fans, robot vacuums, TVs, coffee makers, routers.
Replace with real product discovery when the search layer is built.
"""

from fastapi import APIRouter, HTTPException

from app.requirement_memory import profile_to_requirement_display
from app.schemas import (
    CriterionResult,
    ProductCandidate,
    SearchRequest,
    SearchResponse,
    UserRequirementProfile,
)
from app.session_store import sessions

router = APIRouter()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    session = sessions.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    search_intent = session.get("search_intent")
    if search_intent is None:
        raise HTTPException(status_code=400, detail="Clarify before searching")

    category = search_intent.get("category_label")
    profile = search_intent.get("user_requirement_profile")
    requirements = (
        profile_to_requirement_display(UserRequirementProfile(**profile))
        if profile
        else search_intent.get("requirements", [])
    )

    candidates, recommendation = _run_mock_search(category, requirements)

    return SearchResponse(
        status="complete",
        candidates=candidates,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Mock search dispatcher
# ---------------------------------------------------------------------------

def _run_mock_search(
    category: str | None,
    requirements: list[dict],
) -> tuple[list[ProductCandidate], str]:
    if category == "Ceiling fan":
        return _mock_ceiling_fans(requirements), (
            "Best mock recommendation: Harbor Breeze Mazon 44-in Low Profile. "
            "It is the strongest fit for quiet, low-profile, non-builder-grade bedroom use "
            "while staying under the stated budget."
        )
    if category == "Robot vacuum":
        return _mock_robot_vacuums(requirements), (
            "Best mock recommendation: Roomba Combo j7+. It best fits elderly parents with two dogs "
            "because the self-emptying base reduces maintenance and the mock scoring favors pet hair handling."
        )
    if category == "TV":
        return _mock_tvs(requirements), (
            "Best mock recommendation: Samsung QN90C Neo QLED. It is the strongest fit for a bright room "
            "because the mock scoring prioritizes brightness and glare handling."
        )
    if category == "Coffee maker":
        return _mock_coffee_makers(requirements), (
            "Best mock recommendation: Keurig K-Mini Plus. It best fits a single person on the go "
            "because it is quick, simple, and compact."
        )
    if category == "Router":
        return _mock_routers(requirements), (
            "Best mock recommendation: Eero 6+ Mesh 3-Pack. It best fits a 3-story house because "
            "mesh coverage is safer than relying on one strong router."
        )
    return [], "Mock search supports ceiling fans, robot vacuums, TVs, coffee makers, and routers right now."


# ---------------------------------------------------------------------------
# Criterion helper
# ---------------------------------------------------------------------------

def _criteria_for_product(product: dict, requirements: list[dict]) -> list[CriterionResult]:
    product_results = product["criteria_results"]
    criteria = []
    for requirement in requirements:
        label = requirement["label"]
        result = product_results.get(label, {"met": True, "note": f"Mock result for {requirement['value']}."})
        criteria.append(CriterionResult(label=label, met=result["met"], note=result["note"]))
    return criteria


def _build_candidates(products: list[dict], requirements: list[dict]) -> list[ProductCandidate]:
    return [
        ProductCandidate(
            id=p["id"],
            name=p["name"],
            price=p["price"],
            score=p["score"],
            verdict=p["verdict"],
            criteria=_criteria_for_product(p, requirements),
        )
        for p in products
    ]


# ---------------------------------------------------------------------------
# Mock product data
# ---------------------------------------------------------------------------

def _mock_ceiling_fans(requirements: list[dict]) -> list[ProductCandidate]:
    return _build_candidates(
        [
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
        ],
        requirements,
    )


def _mock_robot_vacuums(requirements: list[dict]) -> list[ProductCandidate]:
    return _build_candidates(
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


def _mock_tvs(requirements: list[dict]) -> list[ProductCandidate]:
    return _build_candidates(
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


def _mock_coffee_makers(requirements: list[dict]) -> list[ProductCandidate]:
    return _build_candidates(
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


def _mock_routers(requirements: list[dict]) -> list[ProductCandidate]:
    return _build_candidates(
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
