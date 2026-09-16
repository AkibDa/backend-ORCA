import sys
import json
import threading
import time
import uuid
import logging
from pathlib import Path
from typing import Any, Dict

from backend.core.config import settings

logger = logging.getLogger(__name__)

PROTO_DIR = Path(__file__).resolve().parents[2] / "Proto"

if str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))

from Proto.conversation.router import llm_route_stateful
from Proto.conversation.state import ConversationState
from Proto.conversation.response import respond
from Proto.location.resolver import extract_location


from backend.db.sessions import ensure_session_exists
from backend.db.conversation_state import (
    get_conversation_state,
    save_conversation_state,
    clear_conversation_state
)
from backend.db.query_history import insert_query_history

_IN_MEMORY_SESSIONS: Dict[str, ConversationState] = {}

class OrcaSessionStore:
    """In-memory session and conversation store for the prototype."""

    def __init__(self) -> None:
        pass

    def get(self, session_id: str, user_id: str) -> ConversationState:
        # In-memory retrieval. If it doesn't exist, we create a new one.
        if session_id not in _IN_MEMORY_SESSIONS:
            _IN_MEMORY_SESSIONS[session_id] = ConversationState()
        return _IN_MEMORY_SESSIONS[session_id]

    def save(self, session_id: str, user_id: str, state: ConversationState) -> None:
        _IN_MEMORY_SESSIONS[session_id] = state

    def clear(self, session_id: str, user_id: str) -> None:
        if session_id in _IN_MEMORY_SESSIONS:
            del _IN_MEMORY_SESSIONS[session_id]



class OrcaService:
    def __init__(self, model, engine, sessions: OrcaSessionStore):
        self.model = model
        self.engine = engine
        self.sessions = sessions

    def process_query(self, query: str, session_id: str | None = None, user_id: str | None = None, location_name: str | None = None, bypass_db_lookup: bool = False) -> Dict[str, Any]:
        request_id = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        deadline = t0 + settings.ORCA_REQUEST_TIMEOUT_SECONDS

        # A missing session_id means this request is stateless.
        # But we require user_id for all stateful requests now.
        if session_id and not user_id:
            raise ValueError("user_id must be provided when session_id is provided")

        t_session_lookup_0 = time.perf_counter()
        state = self.sessions.get(session_id, user_id) if session_id else ConversationState()
        t_session_lookup_ms = (time.perf_counter() - t_session_lookup_0) * 1000.0

        action, plan, extraction, route_timings = llm_route_stateful(
            query=query,
            conv_model=self.model,
            extract_location_fn=extract_location,
            state=state,
            fallback_location=location_name,
        )

        response_text: str | None = None
        execution: Dict[str, Any] | None = None
        segments: list[dict] | None = None

        if action == "CHAT":
            response_text = extraction.chat_reply or "I'm sorry, I don't understand. Could you please rephrase?"

        elif action == "GIVE_UP":
            response_text = (
                "I couldn't identify the location from your query. "
                "Where are you planning to go fishing or navigate?"
            )
            if session_id:
                self.sessions.clear(session_id, user_id)

        elif action == "CLARIFY":
            response_text = extraction.clarify_question or "Could you please specify the exact location or region you are asking about?"

        elif action == "ORCA_QUERY":
            if plan is None:
                raise RuntimeError("ORCA_QUERY returned without a QueryPlan")

            t_engine_0 = time.perf_counter()
            execution = self.engine.run(plan, deadline, request_id=request_id, bypass_db_lookup=bypass_db_lookup)
            t_engine_ms = (time.perf_counter() - t_engine_0) * 1000.0
            
            t_resp_0 = time.perf_counter()
            response_text, segments, response_timings = respond(query, plan, execution, self.model, deadline, request_id=request_id)
            t_response_gen_ms = (time.perf_counter() - t_resp_0) * 1000.0
            if execution:
                execution["response_timings"] = response_timings

        else:
            raise RuntimeError(f"Unknown ORCA action: {action}")

        total_ms = (time.perf_counter() - t0) * 1000.0
        
        if session_id:
            # Save conversation state in-memory
            t_session_save_0 = time.perf_counter()
            self.sessions.save(session_id, user_id, state)
            t_session_save_ms = (time.perf_counter() - t_session_save_0) * 1000.0
            
            # Query history is disabled for the prototype to avoid Supabase RLS issues
            t_history_save_ms = 0.0

        data_freshness = self._evaluate_data_freshness(execution)

        result = {
            "query": query,
            "action": action,
            "response": response_text,
            "segments": segments,
            "plan": plan.model_dump(mode="json") if plan else None,
            "extraction": extraction.model_dump(mode="json"),
            "execution": self._serialize_execution(execution),
            "agent_execution": execution.get("agent_execution") if execution else None,
            "route_timings": route_timings,
            "total_latency_ms": round(total_ms, 2),
            "data_freshness": data_freshness,
        }

        # Structured Observability Logging
        log_data = {
            "session_id": session_id,
            "user_id": user_id,
            "action": action,
            "total_latency_ms": round(total_ms, 2),
            "route_timings": route_timings,
        }
        if execution:
            log_data["stage_timings"] = execution.get("stage_timings", {})
            log_data["agent_timings"] = execution.get("agent_timings", {})
            
            # Check if any agent failed or timed out
            failed_agents = [
                name for name, res in execution.get("context", {}).items()
                if isinstance(res, dict) and res.get("status") != "success" 
                or (hasattr(res, "status") and res.status != "success")
            ]
            if failed_agents:
                log_data["failed_agents"] = failed_agents
                
            rec = execution.get("recommendation", {})
            log_data["decision"] = rec.get("decision")
            log_data["risk_level"] = rec.get("risk_level")

        # Did we exceed the deadline at the end?
        if time.perf_counter() > deadline:
            log_data["deadline_exceeded"] = True

        log_data["request_id"] = request_id
        logger.info(json.dumps(log_data, default=str))

        # PRINT LATENCY BREAKDOWN FOR TERMINAL OBSERVABILITY
        print(f"\n{'═'*80}")
        print("  BACKEND LATENCY BREAKDOWN")
        print(f"{'═'*80}")
        print(f"Session Lookup      : {t_session_lookup_ms:7.1f} ms")
        print(f"Qwen Extract/Route  : {route_timings.get('total_ms', 0):7.1f} ms")
        
        if execution and "stage_timings" in execution:
            st = execution["stage_timings"]
            print(f"Engine Run Total    : {st.get('total_engine_ms', 0):7.1f} ms")
            
            cand_timings = st.get("candidate_timings", [])
            if cand_timings:
                print("\nCANDIDATE LATENCY")
                for c in cand_timings:
                    print(f"  {c['location']:<12} {c['total_ms']:7.1f} ms")
                    
                print("\nTIER LATENCY (Summed across candidates)")
                tier_sums = {}
                for c in cand_timings:
                    for t in c['tiers']:
                        tier_sums[t['tier_name']] = tier_sums.get(t['tier_name'], 0.0) + t['total_ms']
                for t_name, t_ms in sorted(tier_sums.items()):
                    print(f"  {t_name:<12} {t_ms:7.1f} ms")

            print("\nAGENT LATENCY")
            for a_name, a_ms in execution.get("agent_timings", {}).items():
                print(f"  {a_name:<12} {a_ms:7.1f} ms")
                
        if action == "ORCA_QUERY":
            print(f"\nResponse Gen        : {t_response_gen_ms:7.1f} ms")
            if execution and "response_timings" in execution:
                rt = execution["response_timings"]
                print(f"  Prompt Build      : {rt.get('prompt_build_ms', 0):7.1f} ms")
                print(f"  Inference         : {rt.get('inference_ms', 0):7.1f} ms")
                print(f"  Parse             : {rt.get('parse_ms', 0):7.1f} ms")
                print(f"  Deterministic     : {rt.get('deterministic_ms', 0):7.1f} ms")
            
        if session_id:
            print(f"Session Save        : {t_session_save_ms:7.1f} ms")
            print(f"History Save        : {t_history_save_ms:7.1f} ms")
            
        print(f"Total Backend Req   : {total_ms:7.1f} ms")
        print(f"{'═'*80}\n")

        return result

    @staticmethod
    def _serialize_execution(execution: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if execution is None:
            return None

        serialized = dict(execution)
        context = execution.get("context", {})
        serialized["context"] = {
            agent_name: (
                agent_result.model_dump(mode="json")
                if hasattr(agent_result, "model_dump")
                else agent_result
            )
            for agent_name, agent_result in context.items()
        }
        return serialized

    @staticmethod
    def _evaluate_data_freshness(execution: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if not execution or not execution.get("context"):
            return None

        from datetime import datetime, timezone, timedelta
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        
        status = "fresh"
        data_timestamp = None
        valid_until = None
        sources = set()

        context = execution["context"]
        for agent_name, agent_result_dict in context.items():
            if not isinstance(agent_result_dict, dict):
                continue
                
            agent_ts_iso = agent_result_dict.get("timestamp")
            if not agent_ts_iso:
                continue

            if not data_timestamp or agent_ts_iso < data_timestamp:
                data_timestamp = agent_ts_iso
            
            data = agent_result_dict.get("data") or {}
            
            if "observed_at" in data:
                obs_time = data["observed_at"]
                if not data_timestamp or obs_time < data_timestamp:
                    data_timestamp = obs_time
            
            if "valid_until" in data:
                vu = data["valid_until"]
                if not valid_until or vu > valid_until:
                    valid_until = vu
                    
            agent_sources = agent_result_dict.get("sources", [])
            if agent_sources:
                sources.update(agent_sources)
                
            # Basic stale heuristic: if timestamp is old
            if data_timestamp:
                try:
                    dt = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
                    if dt < now_dt - timedelta(hours=6):
                        status = "stale"
                except ValueError:
                    pass

        return {
            "status": status,
            "data_timestamp": data_timestamp or now_iso,
            "checked_at": now_iso,
            "source": ", ".join(sources) if sources else "unknown",
            "offline_cacheable": True,
            "valid_until": valid_until
        }
