from fastapi import APIRouter, HTTPException, Request, Depends
import logging

from backend.schemas.requests import OrcaQueryRequest
from backend.schemas.responses import OrcaQueryResponse
from backend.api.dependencies.auth import get_current_user
from backend.api.dependencies.rate_limit import check_rate_limit, check_rate_limit_unauthenticated, acquire_concurrency_slot
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/orca",
    tags=["ORCA"],
)


@router.post("/query", response_model=OrcaQueryResponse)
def process_query(
    request: OrcaQueryRequest, 
    http_request: Request,
    user_id: str = Depends(check_rate_limit),
    _: None = Depends(acquire_concurrency_slot)
):
    service = http_request.app.state.orca_service

    try:
        return service.process_query(
            query=request.query,
            session_id=request.session_id.strip() if request.session_id and request.session_id.strip() else None,
            user_id=user_id,
            location_name=request.location,
            bypass_db_lookup=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Internal ORCA failure for user {user_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the request.",
        )

@router.post("/command-center/query", response_model=OrcaQueryResponse)
def command_center_query(
    request: OrcaQueryRequest, 
    http_request: Request,
    ip_address: str = Depends(check_rate_limit_unauthenticated),
    _: None = Depends(acquire_concurrency_slot)
):
    if not settings.ORCA_COMMAND_CENTER_ENABLED:
        raise HTTPException(
            status_code=403, 
            detail="Command Center endpoint is disabled."
        )

    service = http_request.app.state.orca_service

    logger.info("[ORCA COMMAND CENTER] query received")

    try:
        result = service.process_query(
            query=request.query,
            session_id=request.session_id.strip() if request.session_id and request.session_id.strip() else None,
            user_id=f"cmd_center_{ip_address}",
            location_name=request.location,
            bypass_db_lookup=True,
        )
        logger.info("[ORCA COMMAND CENTER] query completed")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[ORCA COMMAND CENTER] failure: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the request.",
        )


@router.get("/sessions/{session_id}/history")
def session_history(
    session_id: str, 
    http_request: Request,
    user_id: str = Depends(get_current_user)
):
    from backend.db.query_history import get_session_history
    try:
        history = get_session_history(session_id, user_id)
        return {"session_id": session_id, "history": history}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to fetch session history for {session_id}, user {user_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(exc)}")
