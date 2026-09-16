from backend.db.client import get_supabase_client
from fastapi import HTTPException, status
import time
import logging

logger = logging.getLogger(__name__)

def ensure_session_exists(session_id: str, user_id: str):
    """Ensure a session exists in the database. Creates one if not."""
    client = get_supabase_client()
    
    t0 = time.perf_counter()
    session_resp = client.table("sessions").select("id, user_id").eq("id", session_id).execute()
    print(f"DB TRACE [ensure_session_exists]: sessions.select took {(time.perf_counter() - t0) * 1000:.1f}ms")
    
    if not session_resp.data:
        # Create a new session with the authenticated user_id
        t1 = time.perf_counter()
        client.table("sessions").insert({"id": session_id, "user_id": user_id}).execute()
        print(f"DB TRACE [ensure_session_exists]: sessions.insert took {(time.perf_counter() - t1) * 1000:.1f}ms")
    else:
        # Verify ownership
        existing_user_id = session_resp.data[0].get("user_id")
        if existing_user_id and str(existing_user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session."
            )
