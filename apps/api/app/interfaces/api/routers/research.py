import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.security import rate_limit
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import ResearchRunRequest, ResearchRunResponse, UserPublic
from app.infrastructure.db import research_repository

logger = logging.getLogger("research")

try:
    from apps.agent.research_graph import run_research
except Exception as exc:  # pragma: no cover - import safety
    run_research = None
    logger.error("Failed to import research graph: %s", exc)


router = APIRouter()


@router.post("/research/run", response_model=ResearchRunResponse)
def research_run(
    payload: ResearchRunRequest,
    user: UserPublic = Depends(get_current_user),
) -> ResearchRunResponse:
    # Simple per-user rate limit to avoid runaway agent runs.
    identifier = user.user_id or user.email
    try:
        rate_limit.enforce(bucket="research_run", identifier=identifier, limit=5, window_seconds=60)
    except rate_limit.RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many research runs, slow down.",
        )

    if run_research is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research agent unavailable",
        )

    prompt = payload.prompt.strip()
    if len(prompt) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt too short")
    max_steps = payload.max_search_steps
    existing_trace = payload.trace_id.strip() if payload.trace_id else None

    try:
        result = run_research(
            prompt,
            firm_id=user.firm_id,
            user_id=user.user_id,
            max_search_steps=max_steps,
            trace_id=existing_trace,
        )
    except Exception as exc:  # pragma: no cover - runtime protection
        logger.exception("research_run_error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    trace_id = result.get("trace_id", existing_trace or "")
    run_record = research_repository.upsert_run(
        trace_id=trace_id,
        firm_id=user.firm_id,
        user_id=user.user_id,
        status=result.get("status", "unknown"),
        issues=result.get("issues", []) or [],
        research_plan=result.get("research_plan", []) or [],
        queries=result.get("queries", []) or [],
        briefing=result.get("briefing"),
        errors=[result.get("error")] if result.get("error") else None,
    )

    return ResearchRunResponse(
        trace_id=trace_id,
        status=run_record["status"],
        issues=run_record["issues"] or [],
        research_plan=run_record["research_plan"] or [],
        queries=run_record["queries"] or [],
        briefing=run_record["briefing"],
        errors=run_record["errors"],
    )


@router.get("/research/{trace_id}", response_model=ResearchRunResponse)
def research_get(
    trace_id: str,
    user: UserPublic = Depends(get_current_user),
) -> ResearchRunResponse:
    record = research_repository.get_run(trace_id, firm_id=user.firm_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    return ResearchRunResponse(
        trace_id=record["trace_id"],
        status=record["status"],
        issues=record["issues"] or [],
        research_plan=record["research_plan"] or [],
        queries=record["queries"] or [],
        briefing=record["briefing"],
        errors=record["errors"],
    )
