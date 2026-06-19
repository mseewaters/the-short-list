"""Category router: /api/category-intelligence, /api/category-extract, /api/llm-config.

Provides category schema generation and free-text category extraction from user input.
"""

from fastapi import APIRouter, HTTPException

from app.category_intelligence.extraction import extract_category
from app.category_intelligence.llm import CategoryIntelligenceError, get_llm_config_metadata
from app.category_intelligence.service import get_category_intelligence
from app.schemas import (
    CategoryExtractRequest,
    CategoryExtractResponse,
    CategoryIntelligenceRequest,
    CategoryIntelligenceResponse,
)

router = APIRouter(prefix="/api")


@router.get("/llm-config")
def llm_config():
    return get_llm_config_metadata()


@router.post("/category-intelligence", response_model=CategoryIntelligenceResponse)
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
        category_schema=record.category_schema.model_dump(),
        cached=cached,
    )


@router.post("/category-extract", response_model=CategoryExtractResponse)
def category_extract(request: CategoryExtractRequest):
    try:
        return CategoryExtractResponse(**extract_category(request.user_input, request.additional_context))
    except CategoryIntelligenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
