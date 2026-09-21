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
        try:
            client.table("sessions").insert({"id": session_id, "user_id": user_id}).execute()
        except Exception as e:
            # 23505 is the PostgreSQL error code for unique_violation
            if hasattr(e, "message") and isinstance(e.message, dict) and e.message.get("code") == "23505":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This session ID is already in use by another user."
                )
            elif hasattr(e, "code") and e.code == "23505":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This session ID is already in use by another user."
                )
            # Sometimes the exception is postgrest.exceptions.APIError with a dict representation
            elif "23505" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This session ID is already in use by another user."
                )
            raise e
        print(f"DB TRACE [ensure_session_exists]: sessions.insert took {(time.perf_counter() - t1) * 1000:.1f}ms")
    else:
        # Verify ownership
        existing_user_id = session_resp.data[0].get("user_id")
        if existing_user_id and str(existing_user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session."
            )

def get_or_create_latest_session(user_id: str) -> str:
    """Retrieve the user's most recent session, or create a new one if none exist."""
    client = get_supabase_client()
    import uuid
    
    # Try to find the most recently created session for this user
    try:
        resp = client.table("sessions").select("id").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        if resp.data:
            return resp.data[0]["id"]
    except Exception as e:
        logger.error(f"Error fetching latest session for user {user_id}: {e}")
        # Fall through to create a new session if select fails
        
    # Create a new session if none found
    new_session_id = str(uuid.uuid4())
    ensure_session_exists(new_session_id, user_id)
    return new_session_id
