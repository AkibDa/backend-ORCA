from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.db.client import get_supabase_client
from backend.db.marine.db_reliability import with_db_reliability

def _is_pfz_valid(pfz: Dict[str, Any], now: datetime) -> bool:
    try:
        valid_from_str = pfz.get("valid_from")
        if not valid_from_str:
            return False
            
        if valid_from_str.endswith('Z'):
            valid_from_str = valid_from_str[:-1] + '+00:00'
        valid_from = datetime.fromisoformat(valid_from_str)
        if valid_from.tzinfo is None:
            valid_from = valid_from.replace(tzinfo=timezone.utc)
            
        if valid_from > now:
            return False
            
        valid_until_str = pfz.get("valid_until")
        if valid_until_str:
            if valid_until_str.endswith('Z'):
                valid_until_str = valid_until_str[:-1] + '+00:00'
            valid_until = datetime.fromisoformat(valid_until_str)
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            if valid_until < now:
                return False
                
        return True
    except (ValueError, TypeError):
        return False

@with_db_reliability(max_retries=2)
def get_active_pfz_zones() -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = client.table("pfz_zones").select("*").eq("is_active", True).execute()
    now = datetime.now(timezone.utc)
    return [zone for zone in resp.data if _is_pfz_valid(zone, now)]

@with_db_reliability(max_retries=2)
def get_nearby_pfz_zones(lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = client.rpc("get_pfz_within_radius", {
        "p_lat": lat,
        "p_lon": lon,
        "p_radius_km": radius_km
    }).execute()
    
    now = datetime.now(timezone.utc)
    return [zone for zone in resp.data if _is_pfz_valid(zone, now)]

@with_db_reliability(max_retries=2)
def upsert_pfz_zone(pfz_data: Dict[str, Any]) -> None:
    client = get_supabase_client()
    client.table("pfz_zones").upsert(pfz_data).execute()
