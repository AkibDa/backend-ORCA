from backend.db.client import get_supabase_client
from backend.db.sessions import ensure_session_exists
import time
import logging

logger = logging.getLogger(__name__)

def insert_query_history(history_data: dict) -> None:
    client = get_supabase_client()
    t0 = time.perf_counter()
    client.table("query_history").insert(history_data).execute()
    print(f"DB TRACE [insert_query_history]: query_history.insert took {(time.perf_counter() - t0) * 1000:.1f}ms")

def get_session_history(session_id: str, user_id: str) -> list:
    # Ensure the user actually owns this session before returning history
    ensure_session_exists(session_id, user_id)
    
    client = get_supabase_client()
    t0 = time.perf_counter()
    resp = client.table("query_history").select("query, response, action, created_at").eq("session_id", session_id).order("created_at").execute()
    print(f"DB TRACE [get_session_history]: query_history.select took {(time.perf_counter() - t0) * 1000:.1f}ms")
    return resp.data
