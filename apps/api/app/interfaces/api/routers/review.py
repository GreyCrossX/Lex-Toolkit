import json
import logging
import uuid
from time import perf_counter
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.infrastructure.security import rate_limit
from app.interfaces.api.routers.auth import get_current_user
from app.interfaces.api.schemas import ReviewRequest, ReviewResponse, UserPublic
from app.infrastructure.db import review_repository
from langchain_core.messages import HumanMessage

logger = logging.getLogger("review")

try:
    from apps.agent.review_graph import build_review_graph, run_review
except Exception as exc:  # pragma: no cover
    run_review = None
    build_review_graph = None
    logger.error("Failed to import review graph: %s", exc)


router = APIRouter()


@router.get("/review/health")
def review_health() -> dict:
    return {"status": "ok", "service": "review"}


def _review_rate_limit(identifier: str, bucket: str = "review_run") -> None:
    try:
        rate_limit.enforce(
            bucket=bucket, identifier=identifier, limit=5, window_seconds=60
        )
    except rate_limit.RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many review runs, slow down.",
        )


@router.post("/review/run", response_model=ReviewResponse)
def review_run(
    payload: ReviewRequest, user: UserPublic = Depends(get_current_user)
) -> ReviewResponse:
    identifier = user.user_id or user.email
    _review_rate_limit(identifier, bucket="review_run")

    if run_review is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review agent unavailable",
        )

    trace_id = payload.research_trace_id or uuid.uuid4().hex
    started = perf_counter()
    try:
        result = run_review(
            payload.model_dump(),
            firm_id=user.firm_id,
            user_id=user.user_id,
            trace_id=trace_id,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception(
            "review_run_error",
            extra={
                "trace_id": trace_id,
                "user_id": user.user_id,
                "firm_id": user.firm_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    run_record = review_repository.upsert_run(
        trace_id=result.get("trace_id", trace_id),
        firm_id=user.firm_id,
        user_id=user.user_id,
        status=result.get("status", "answered"),
        doc_type=payload.doc_type,
        structural_findings=result.get("structural_findings", []),
        issues=result.get("issues", []),
        suggestions=result.get("suggestions", []),
        qa_notes=result.get("qa_notes", []),
        residual_risks=result.get("residual_risks", []),
        summary=result.get("summary"),
        conflict_check=result.get("conflict_check"),
        errors=[result.get("error")] if result.get("error") else None,
    )
    elapsed = perf_counter() - started
    logger.info(
        "review_run_completed",
        extra={
            "trace_id": run_record["trace_id"],
            "user_id": user.user_id,
            "firm_id": user.firm_id,
            "status": run_record["status"],
            "elapsed_ms": round(elapsed * 1000, 2),
        },
    )

    return ReviewResponse(
        trace_id=run_record["trace_id"],
        status=run_record["status"],
        doc_type=run_record["doc_type"],
        structural_findings=run_record["structural_findings"] or [],
        issues=run_record["issues"] or [],
        suggestions=run_record["suggestions"] or [],
        qa_notes=run_record["qa_notes"] or [],
        residual_risks=run_record["residual_risks"] or [],
        summary=run_record["summary"],
        conflict_check=run_record["conflict_check"],
        errors=run_record["errors"],
    )


@router.get("/review/{trace_id}", response_model=ReviewResponse)
def review_get(
    trace_id: str, user: UserPublic = Depends(get_current_user)
) -> ReviewResponse:
    record = review_repository.get_run(trace_id, firm_id=user.firm_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found"
        )
    return ReviewResponse(
        trace_id=record["trace_id"],
        status=record["status"],
        doc_type=record["doc_type"],
        structural_findings=record["structural_findings"] or [],
        issues=record["issues"] or [],
        suggestions=record["suggestions"] or [],
        qa_notes=record["qa_notes"] or [],
        residual_risks=record["residual_risks"] or [],
        summary=record["summary"],
        conflict_check=record["conflict_check"],
        errors=record["errors"],
    )


@router.post("/review/run/stream")
def review_run_stream(
    payload: ReviewRequest, user: UserPublic = Depends(get_current_user)
) -> StreamingResponse:
    identifier = user.user_id or user.email
    _review_rate_limit(identifier, bucket="review_stream")

    if run_review is None or build_review_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review agent unavailable",
        )

    trace_id = payload.research_trace_id or uuid.uuid4().hex
    graph = build_review_graph().compile()

    def event_stream() -> Generator[bytes, None, None]:
        current_state = {
            "trace_id": trace_id,
            "status": "running",
            "doc_type": payload.doc_type,
            "structural_findings": [],
            "issues": [],
            "suggestions": [],
            "qa_notes": [],
            "residual_risks": [],
            "summary": None,
            "conflict_check": None,
            "errors": None,
        }

        def dumps(obj: dict) -> str:
            return json.dumps(obj, default=str)

        started = perf_counter()
        yield (
            dumps({"type": "start", "trace_id": trace_id, "status": "running"}) + "\n"
        ).encode("utf-8")
        try:
            initial_state = {
                **payload.model_dump(),
                "trace_id": trace_id,
                "firm_id": user.firm_id,
                "user_id": user.user_id,
                "messages": [HumanMessage(content=payload.text or "")],
            }
            logger.info(
                "review_stream_start",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                },
            )
            run_record = review_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="running",
                doc_type=payload.doc_type,
                structural_findings=[],
                issues=[],
                suggestions=[],
                qa_notes=[],
                residual_risks=[],
                summary=None,
                conflict_check=None,
                errors=None,
            )
            for update in graph.stream(initial_state, stream_mode="updates"):
                if not isinstance(update, dict):
                    continue
                current_state.update(update)
                run_record = review_repository.upsert_run(
                    trace_id=trace_id,
                    firm_id=user.firm_id,
                    user_id=user.user_id,
                    status=current_state.get("status", "running"),
                    doc_type=current_state.get("doc_type", payload.doc_type),
                    structural_findings=current_state.get("structural_findings", []),
                    issues=current_state.get("issues", []),
                    suggestions=current_state.get("suggestions", []),
                    qa_notes=current_state.get("qa_notes", []),
                    residual_risks=current_state.get("residual_risks", []),
                    summary=current_state.get("summary"),
                    conflict_check=current_state.get("conflict_check"),
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
                "review_stream_done",
                extra={
                    "trace_id": trace_id,
                    "user_id": user.user_id,
                    "firm_id": user.firm_id,
                    "status": current_state.get("status"),
                    "elapsed_ms": round(elapsed * 1000, 2),
                },
            )
            yield (
                dumps({"type": "done", "trace_id": trace_id, **current_state}) + "\n"
            ).encode("utf-8")
        except Exception as exc:  # pragma: no cover
            logger.exception("review_stream_error", extra={"trace_id": trace_id})
            review_repository.upsert_run(
                trace_id=trace_id,
                firm_id=user.firm_id,
                user_id=user.user_id,
                status="error",
                doc_type=payload.doc_type,
                structural_findings=current_state.get("structural_findings", []),
                issues=current_state.get("issues", []),
                suggestions=current_state.get("suggestions", []),
                qa_notes=current_state.get("qa_notes", []),
                residual_risks=current_state.get("residual_risks", []),
                summary=current_state.get("summary"),
                conflict_check=current_state.get("conflict_check"),
                errors=[str(exc)],
            )
            yield (
                dumps({"type": "error", "trace_id": trace_id, "error": str(exc)}) + "\n"
            ).encode("utf-8")

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
