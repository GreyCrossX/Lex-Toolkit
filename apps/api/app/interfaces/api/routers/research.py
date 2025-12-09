import json
import logging
import uuid
from typing import Generator, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.security import rate_limit
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import ResearchRunRequest, ResearchRunResponse, UserPublic
from app.infrastructure.db import research_repository
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

logger = logging.getLogger("research")

try:
    from apps.agent.research_graph import build_research_graph, run_research
except Exception as exc:  # pragma: no cover - import safety
    run_research = None
    build_research_graph = None
    logger.error("Failed to import research graph: %s", exc)


router = APIRouter()


def _research_rate_limit(identifier: str, bucket: str = "research_run") -> None:
    try:
        rate_limit.enforce(bucket=bucket, identifier=identifier, limit=5, window_seconds=60)
    except rate_limit.RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many research runs, slow down.",
        )


@router.post("/research/run", response_model=ResearchRunResponse)
def research_run(
    payload: ResearchRunRequest,
    user: UserPublic = Depends(get_current_user),
) -> ResearchRunResponse:
    # Simple per-user rate limit to avoid runaway agent runs.
    identifier = user.user_id or user.email
    _research_rate_limit(identifier, bucket="research_run")

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


@router.post("/research/run/stream")
def research_run_stream(
    payload: ResearchRunRequest,
    user: UserPublic = Depends(get_current_user),
) -> StreamingResponse:
    """
    Experimental streaming version of research run, emitting NDJSON events.
    """
    identifier = user.user_id or user.email
    _research_rate_limit(identifier, bucket="research_stream")

    if run_research is None or build_research_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research agent unavailable",
        )

    prompt = payload.prompt.strip()
    if len(prompt) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt too short")
    max_steps = payload.max_search_steps
    existing_trace = payload.trace_id.strip() if payload.trace_id else None
    trace_id = existing_trace or uuid.uuid4().hex

    graph = build_research_graph().compile()

    def event_stream() -> Generator[bytes, None, None]:
        current_state = {
            "trace_id": trace_id,
            "status": "running",
            "issues": [],
            "research_plan": [],
            "queries": [],
            "briefing": None,
            "errors": None,
        }

        def merge_update(update: dict) -> None:
            for key, val in update.items():
                current_state[key] = val

        def snapshot_payload() -> dict:
            return {
                "trace_id": trace_id,
                "status": current_state.get("status") or "unknown",
                "issues": current_state.get("issues") or [],
                "research_plan": current_state.get("research_plan") or [],
                "queries": current_state.get("queries") or [],
                "briefing": current_state.get("briefing"),
                "errors": current_state.get("errors"),
            }

        # Initial event so the client can show progress immediately.
        yield (json.dumps({"type": "start", "trace_id": trace_id, "status": "running"}) + "\n").encode("utf-8")
        try:
            initial_state = {
                "messages": [HumanMessage(content=prompt)],
                "trace_id": trace_id,
                "firm_id": user.firm_id,
                "user_id": user.user_id,
                "status": "running",
            }
            if max_steps:
                initial_state["max_search_steps"] = max_steps

            logger.info(
                "research_stream_start",
                extra={"trace_id": trace_id, "user_id": user.user_id, "firm_id": user.firm_id},
            )
            for update in graph.stream(initial_state, stream_mode="updates"):
                if not isinstance(update, dict):
                    continue
                merge_update(update)
                yield (
                    json.dumps({"type": "update", "trace_id": trace_id, "data": update, "status": current_state["status"]})
                    + "\n"
                ).encode("utf-8")

            snapshot = snapshot_payload()
            run_record = research_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status=snapshot["status"],
                issues=snapshot["issues"],
                research_plan=snapshot["research_plan"],
                queries=snapshot["queries"],
                briefing=snapshot["briefing"],
                errors=snapshot["errors"],
            )
            snapshot["status"] = run_record["status"]
            logger.info(
                "research_stream_done",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                    "status": snapshot["status"],
                },
            )
            yield (json.dumps({"type": "done", **snapshot}) + "\n").encode("utf-8")
        except Exception as exc:  # pragma: no cover - runtime protection
            logger.exception("research_run_stream_error")
            research_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="error",
                issues=current_state.get("issues") or [],
                research_plan=current_state.get("research_plan") or [],
                queries=current_state.get("queries") or [],
                briefing=current_state.get("briefing"),
                errors=[str(exc)],
            )
            yield (json.dumps({"type": "error", "trace_id": trace_id, "error": str(exc)}) + "\n").encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
