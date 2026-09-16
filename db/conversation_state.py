from backend.db.client import get_supabase_client
from Proto.conversation.state import ConversationState
import time
import logging

logger = logging.getLogger(__name__)

def get_conversation_state(session_id: str) -> ConversationState:
    client = get_supabase_client()
    t0 = time.perf_counter()
    state_resp = client.table("conversation_state").select("*").eq("session_id", session_id).execute()
    print(f"DB TRACE [get_conversation_state]: conversation_state.select took {(time.perf_counter() - t0) * 1000:.1f}ms")
    if state_resp.data:
        data = state_resp.data[0]
        return ConversationState(
            language=data.get("language"),
            intent=data.get("intent"),
            action_type=data.get("action_type"),
            location_text=data.get("location_text"),
            reference_location_text=data.get("reference_location_text"),
            target_location_text=data.get("target_location_text"),
            region_locations=data.get("region_locations") or [],
            location_role=data.get("location_role"),
            activity=data.get("activity"),
            time_relative=data.get("time_relative"),
            time_offset_days=data.get("time_offset_days"),
            time_period=data.get("time_period"),
            user_constraint=data.get("user_constraint"),
            pending_clarification=data.get("pending_clarification"),
            clarify_rounds=data.get("clarify_rounds") or 0
        )
    return ConversationState()

def save_conversation_state(session_id: str, state: ConversationState) -> None:
    client = get_supabase_client()
    data = {
        "session_id": session_id,
        "language": state.language,
        "intent": state.intent,
        "action_type": state.action_type,
        "location_text": state.location_text,
        "reference_location_text": state.reference_location_text,
        "target_location_text": state.target_location_text,
        "region_locations": state.region_locations,
        "location_role": state.location_role,
        "activity": state.activity,
        "time_relative": state.time_relative,
        "time_offset_days": state.time_offset_days,
        "time_period": state.time_period,
        "user_constraint": state.user_constraint,
        "pending_clarification": state.pending_clarification,
        "clarify_rounds": state.clarify_rounds
    }
    t0 = time.perf_counter()
    client.table("conversation_state").upsert(data).execute()
    print(f"DB TRACE [save_conversation_state]: conversation_state.upsert took {(time.perf_counter() - t0) * 1000:.1f}ms")

def clear_conversation_state(session_id: str) -> None:
    client = get_supabase_client()
    t0 = time.perf_counter()
    client.table("conversation_state").delete().eq("session_id", session_id).execute()
    print(f"DB TRACE [clear_conversation_state]: conversation_state.delete took {(time.perf_counter() - t0) * 1000:.1f}ms")
