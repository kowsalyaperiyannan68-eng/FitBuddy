"""HTTP routes for FitBuddy."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from . import config
from .ai import generate_plan
from .database import list_plans, save_plan
from .schemas import PlanRequest, PlanResponse

router = APIRouter()

# The HTML lives in the project-level ``template/`` directory.
templates = Jinja2Templates(directory="template")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page UI."""
    return templates.TemplateResponse(
        request,
        "indexs.html",
        {"ai_available": config.ai_available()},
    )


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "ai_available": config.ai_available(),
        "mode": "gemini" if config.ai_available() else "demo",
    }


@router.post("/api/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest):
    """Generate a fitness + nutrition plan and persist it."""
    plan, source = await generate_plan(req)
    try:
        plan_id = save_plan(
            name=req.name,
            goal=req.goal,
            source=source,
            request=req.model_dump(),
            plan=plan,
        )
    except Exception:
        plan_id = None  # Persistence is best-effort; still return the plan.

    return PlanResponse(
        id=plan_id,
        source=source,
        summary=plan.get("summary", {}),
        workout=plan.get("workout", {}),
        nutrition=plan.get("nutrition", {}),
    )


@router.get("/api/plans")
async def get_plans():
    """List recently generated plans (admin-gated)."""
    if not config.ADMIN_ENABLED:
        raise HTTPException(status_code=403, detail="Admin endpoints are disabled.")
    return JSONResponse(list_plans())
