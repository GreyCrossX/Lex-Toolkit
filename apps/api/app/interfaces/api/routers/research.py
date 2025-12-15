import json
import logging
import uuid
from time import perf_counter
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status

from app.infrastructure.security import rate_limit
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import (
    ResearchRunRequest,
    ResearchRunResponse,
    UserPublic,
)
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


@router.get("/research/health")
def research_health() -> dict:
    return {"status": "ok", "service": "research"}


def _research_rate_limit(identifier: str, bucket: str = "research_run") -> None:
    try:
        rate_limit.enforce(
            bucket=bucket, identifier=identifier, limit=5, window_seconds=60
        )
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt too short"
        )
    max_steps = payload.max_search_steps
    existing_trace = payload.trace_id.strip() if payload.trace_id else None
    logger.info(
        "research_run_start",
        extra={
            "trace_id": existing_trace,
            "user_id": user.user_id,
            "firm_id": user.firm_id,
            "max_steps": max_steps,
        },
    )
    started = perf_counter()

    try:
        result = run_research(
            prompt,
            firm_id=user.firm_id,
            user_id=user.user_id,
            max_search_steps=max_steps,
            trace_id=existing_trace,
        )
    except Exception as exc:  # pragma: no cover - runtime protection
        logger.exception(
            "research_run_error",
            extra={
                "user_id": user.user_id,
                "firm_id": user.firm_id,
                "trace_id": existing_trace,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{exc} (trace_id={existing_trace or 'unassigned'})",
        ) from exc

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
        conflict_check=result.get("conflict_check"),
        errors=[result.get("error")] if result.get("error") else None,
    )
    elapsed = perf_counter() - started
    logger.info(
        "research_run_completed",
        extra={
            "trace_id": trace_id,
            "user_id": user.user_id,
            "firm_id": user.firm_id,
            "status": run_record["status"],
            "elapsed_ms": round(elapsed * 1000, 2),
            "issues": len(run_record["issues"] or []),
            "queries": len(run_record["queries"] or []),
        },
    )

    return ResearchRunResponse(
        trace_id=trace_id,
        status=run_record["status"],
        issues=run_record["issues"] or [],
        research_plan=run_record["research_plan"] or [],
        queries=run_record["queries"] or [],
        briefing=run_record["briefing"],
        conflict_check=run_record.get("conflict_check"),
        errors=run_record["errors"],
    )


@router.get("/research/{trace_id}", response_model=ResearchRunResponse)
def research_get(
    trace_id: str,
    user: UserPublic = Depends(get_current_user),
) -> ResearchRunResponse:
    record = research_repository.get_run(trace_id, firm_id=user.firm_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found"
        )

    return ResearchRunResponse(
        trace_id=record["trace_id"],
        status=record["status"],
        issues=record["issues"] or [],
        research_plan=record["research_plan"] or [],
        queries=record["queries"] or [],
        briefing=record["briefing"],
        conflict_check=record.get("conflict_check"),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt too short"
        )
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
            "conflict_check": None,
            "errors": None,
        }

        def merge_update(update: dict) -> None:
            mapped: dict = {}

            # Pull top-level fields if present directly.
            for field in (
                "issues",
                "research_plan",
                "queries",
                "briefing",
                "conflict_check",
                "errors",
                "status",
            ):
                if field in update:
                    mapped[field] = update[field]

            # Map nested nodes from the research graph into the top-level snapshot.
            if "issue_generator" in update and isinstance(
                update["issue_generator"], dict
            ):
                mapped["issues"] = update["issue_generator"].get(
                    "issues", mapped.get("issues")
                )
            if "research_plan_builder" in update and isinstance(
                update["research_plan_builder"], dict
            ):
                mapped["research_plan"] = update["research_plan_builder"].get(
                    "research_plan", mapped.get("research_plan")
                )
                mapped["status"] = update["research_plan_builder"].get(
                    "status", mapped.get("status")
                )
            if "run_next_search_step" in update and isinstance(
                update["run_next_search_step"], dict
            ):
                rns = update["run_next_search_step"]
                mapped["research_plan"] = rns.get(
                    "research_plan", mapped.get("research_plan")
                )
                mapped["queries"] = rns.get("queries", mapped.get("queries"))
                mapped["status"] = rns.get("status", mapped.get("status"))
            if "synthesize_briefing" in update and isinstance(
                update["synthesize_briefing"], dict
            ):
                mapped["briefing"] = update["synthesize_briefing"].get(
                    "briefing", mapped.get("briefing")
                )
                mapped["status"] = update["synthesize_briefing"].get(
                    "status", mapped.get("status")
                )
            if "conflict_check" in update and isinstance(
                update["conflict_check"], dict
            ):
                mapped["conflict_check"] = update["conflict_check"]
                if update["conflict_check"].get("conflict_found"):
                    logger.info(
                        "conflict_found_stream",
                        extra={
                            "trace_id": trace_id,
                            "user_id": user.user_id,
                            "firm_id": user.firm_id,
                            "opposing": update["conflict_check"].get(
                                "opposing_parties"
                            ),
                        },
                    )

            # Apply mapped top-level values first.
            for key, val in mapped.items():
                if val is not None:
                    current_state[key] = val

            # Then store the raw update payload for completeness.
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
                "conflict_check": current_state.get("conflict_check"),
                "errors": current_state.get("errors"),
            }

        # Initial event so the client can show progress immediately.
        def dumps(obj: dict) -> str:
            return json.dumps(obj, default=str)

        HEARTBEAT_SECONDS = 15
        last_emit = perf_counter()

        def emit(payload: dict) -> bytes:
            nonlocal last_emit
            last_emit = perf_counter()
            return (dumps(payload) + "\n").encode("utf-8")

        started = perf_counter()
        yield emit({"type": "start", "trace_id": trace_id, "status": "running"})
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
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                },
            )
            run_record = research_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status=current_state["status"],
                issues=current_state["issues"],
                research_plan=current_state["research_plan"],
                queries=current_state["queries"],
                briefing=current_state["briefing"],
                conflict_check=current_state["conflict_check"],
                errors=current_state["errors"],
            )
            for update in graph.stream(initial_state, stream_mode="updates"):
                if not isinstance(update, dict):
                    continue
                # Heartbeat to keep connections alive if upstream pauses.
                now = perf_counter()
                if now - last_emit > HEARTBEAT_SECONDS:
                    yield emit(
                        {
                            "type": "keepalive",
                            "trace_id": trace_id,
                            "status": current_state.get("status", "running"),
                        }
                    )
                merge_update(update)
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
                    conflict_check=snapshot.get("conflict_check"),
                    errors=snapshot["errors"],
                )
                payload = {
                    "type": "update",
                    "trace_id": trace_id,
                    "data": update,
                    "status": run_record["status"],
                }
                yield emit(payload)

            snapshot = snapshot_payload()
            if run_record:
                snapshot["status"] = run_record["status"]
            else:
                run_record = research_repository.upsert_run(
                    trace_id=trace_id,
                    firm_id=user.firm_id,
                    user_id=user.user_id,
                    status=snapshot["status"],
                    issues=snapshot["issues"],
                    research_plan=snapshot["research_plan"],
                    queries=snapshot["queries"],
                    briefing=snapshot["briefing"],
                    conflict_check=snapshot.get("conflict_check"),
                    errors=snapshot["errors"],
                )
                snapshot["status"] = run_record["status"]
            elapsed = perf_counter() - started
            logger.info(
                "research_stream_done",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                    "status": snapshot["status"],
                    "issues": len(snapshot.get("issues") or []),
                    "queries": len(snapshot.get("queries") or []),
                    "elapsed_ms": round(elapsed * 1000, 2),
                },
            )
            yield emit({"type": "done", **snapshot})
        except Exception as exc:  # pragma: no cover - runtime protection
            logger.exception(
                "research_run_stream_error",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                },
            )
            research_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="error",
                issues=current_state.get("issues") or [],
                research_plan=current_state.get("research_plan") or [],
                queries=current_state.get("queries") or [],
                briefing=current_state.get("briefing"),
                conflict_check=current_state.get("conflict_check"),
                errors=[str(exc)],
            )
            yield emit({"type": "error", "trace_id": trace_id, "error": str(exc)})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
