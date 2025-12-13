import json
import logging
import uuid
from time import perf_counter
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.infrastructure.security import rate_limit
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import (
    DraftRequest,
    DraftResponse,
    UserPublic,
)
from app.infrastructure.db import draft_repository
from langchain_core.messages import HumanMessage

logger = logging.getLogger("drafting")

try:
    from apps.agent.drafting_graph import run_draft, build_drafting_graph
except Exception as exc:  # pragma: no cover
    run_draft = None
    build_drafting_graph = None
    logger.error("Failed to import drafting graph: %s", exc)


router = APIRouter()


def _draft_rate_limit(identifier: str, bucket: str = "draft_run") -> None:
    try:
        rate_limit.enforce(
            bucket=bucket, identifier=identifier, limit=5, window_seconds=60
        )
    except rate_limit.RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many drafting runs, slow down.",
        )


@router.post("/draft/run", response_model=DraftResponse)
def draft_run(payload: DraftRequest, user: UserPublic = Depends(get_current_user)) -> DraftResponse:
    identifier = user.user_id or user.email
    _draft_rate_limit(identifier, bucket="draft_run")

    if run_draft is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drafting agent unavailable",
        )

    trace_id = payload.research_trace_id or uuid.uuid4().hex
    started = perf_counter()
    try:
        result = run_draft(
            payload.model_dump(),
            firm_id=user.firm_id,
            user_id=user.user_id,
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("draft_run_error", extra={"trace_id": trace_id, "user_id": user.user_id, "firm_id": user.firm_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    run_record = draft_repository.upsert_run(
        trace_id=result.get("trace_id", trace_id),
        firm_id=user.firm_id,
        user_id=user.user_id,
        status=result.get("status", "answered"),
        doc_type=result.get("doc_type") or payload.doc_type,
        plan=result.get("plan", []),
        sections=result.get("draft_sections", []),
        draft=result.get("draft"),
        assumptions=(result.get("review") or {}).get("assumptions"),
        open_questions=(result.get("review") or {}).get("open_questions"),
        risks=(result.get("review") or {}).get("risks"),
        errors=[result.get("error")] if result.get("error") else None,
    )
    elapsed = perf_counter() - started
    logger.info(
        "draft_run_completed",
        extra={
            "trace_id": run_record["trace_id"],
            "user_id": user.user_id,
            "firm_id": user.firm_id,
            "status": run_record["status"],
            "elapsed_ms": round(elapsed * 1000, 2),
        },
    )

    return DraftResponse(
        trace_id=run_record["trace_id"],
        status=run_record["status"],
        doc_type=run_record["doc_type"],
        draft=run_record["draft"] or "",
        sections=run_record["sections"] or [],
        assumptions=run_record["assumptions"] or [],
        open_questions=run_record["open_questions"] or [],
        risks=run_record["risks"] or [],
        errors=run_record["errors"] or None,
    )


@router.get("/draft/{trace_id}", response_model=DraftResponse)
def draft_get(trace_id: str, user: UserPublic = Depends(get_current_user)) -> DraftResponse:
    record = draft_repository.get_run(trace_id, firm_id=user.firm_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return DraftResponse(
        trace_id=record["trace_id"],
        status=record["status"],
        doc_type=record["doc_type"],
        draft=record["draft"] or "",
        sections=record["sections"] or [],
        assumptions=record["assumptions"] or [],
        open_questions=record["open_questions"] or [],
        risks=record["risks"] or [],
        errors=record["errors"] or None,
    )


@router.post("/draft/run/stream")
def draft_run_stream(
    payload: DraftRequest,
    user: UserPublic = Depends(get_current_user),
) -> StreamingResponse:
    identifier = user.user_id or user.email
    _draft_rate_limit(identifier, bucket="draft_stream")

    if run_draft is None or build_drafting_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Drafting agent unavailable",
        )

    trace_id = payload.research_trace_id or uuid.uuid4().hex
    graph = build_drafting_graph().compile()

    def event_stream() -> Generator[bytes, None, None]:
        current_state = {
            "trace_id": trace_id,
            "status": "running",
            "doc_type": payload.doc_type,
            "sections": [],
            "draft": "",
            "assumptions": [],
            "open_questions": [],
            "risks": [],
            "errors": None,
        }

        def dumps(obj: dict) -> str:
            return json.dumps(obj, default=str)

        started = perf_counter()
        yield (dumps({"type": "start", "trace_id": trace_id, "status": "running"}) + "\n").encode("utf-8")
        try:
            initial_state = {
                **payload.model_dump(),
                "trace_id": trace_id,
                "firm_id": user.firm_id,
                "user_id": user.user_id,
                "messages": [HumanMessage(content=payload.context or "")],
            }
            logger.info(
                "draft_stream_start",
                extra={"trace_id": trace_id, "user_id": user.user_id, "firm_id": user.firm_id},
            )
            run_record = draft_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="running",
                doc_type=payload.doc_type,
                plan=[],
                sections=[],
                draft="",
                assumptions=[],
                open_questions=[],
                risks=[],
                errors=None,
            )
            for update in graph.stream(initial_state, stream_mode="updates"):
                if not isinstance(update, dict):
                    continue
                current_state.update(update)
                run_record = draft_repository.upsert_run(
                    trace_id=trace_id,
                    firm_id=user.firm_id,
                    user_id=user.user_id,
                    status=current_state.get("status", "running"),
                    doc_type=current_state.get("doc_type", payload.doc_type),
                    plan=current_state.get("plan", []),
                    sections=current_state.get("draft_sections", []),
                    draft=current_state.get("draft", ""),
                    assumptions=(current_state.get("review") or {}).get("assumptions"),
                    open_questions=(current_state.get("review") or {}).get("open_questions"),
                    risks=(current_state.get("review") or {}).get("risks"),
                    errors=current_state.get("errors"),
                )
                yield (
                    dumps(
                        {
                            "type": "update",
                            "trace_id": trace_id,
                            "status": run_record["status"],
                            "data": update,
                        }
                    )
                    + "\n"
                ).encode("utf-8")

            elapsed = perf_counter() - started
            logger.info(
                "draft_stream_done",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                    "status": current_state.get("status"),
                    "elapsed_ms": round(elapsed * 1000, 2),
                },
            )
            yield (dumps({"type": "done", "trace_id": trace_id, **current_state}) + "\n").encode("utf-8")
        except Exception as exc:  # pragma: no cover
            logger.exception("draft_stream_error", extra={"trace_id": trace_id})
            draft_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="error",
                doc_type=payload.doc_type,
                plan=current_state.get("plan", []),
                sections=current_state.get("draft_sections", []),
                draft=current_state.get("draft", ""),
                assumptions=(current_state.get("review") or {}).get("assumptions"),
                open_questions=(current_state.get("review") or {}).get("open_questions"),
                risks=(current_state.get("review") or {}).get("risks"),
                errors=[str(exc)],
            )
            yield (dumps({"type": "error", "trace_id": trace_id, "error": str(exc)}) + "\n").encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
