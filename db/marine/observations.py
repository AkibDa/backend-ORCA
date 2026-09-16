from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from backend.db.client import get_supabase_client
from backend.core.config import settings
from backend.db.marine.db_reliability import with_db_reliability

@with_db_reliability(max_retries=2)
def get_latest_observations(lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = client.rpc("get_observations_within_radius", {
        "p_lat": lat,
        "p_lon": lon,
        "p_radius_km": radius_km
    }).execute()
    
    # Filter by freshness
    valid_observations = []
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=settings.WEATHER_DATA_MAX_AGE_HOURS)
    
    for obs in resp.data:
        observed_at_str = obs.get("observed_at")
        if not observed_at_str:
            continue
            
        try:
            # Parse ISO format, handle Z
            if observed_at_str.endswith('Z'):
                observed_at_str = observed_at_str[:-1] + '+00:00'
            observed_at = datetime.fromisoformat(observed_at_str)
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
                
            if now - observed_at <= max_age:
                valid_observations.append(obs)
        except (ValueError, TypeError):
            pass
            
    return valid_observations

@with_db_reliability(max_retries=2)
def upsert_observation(obs_data: Dict[str, Any]) -> None:
    client = get_supabase_client()
    # Upsert requires unique constraint on location/source or ID
    client.table("marine_observations").upsert(obs_data).execute()

@with_db_reliability(max_retries=2)
def get_observations_by_region(region_name: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = client.table("marine_observations").select("*").ilike("region", f"%{region_name}%").order("timestamp", desc=True).limit(50).execute()
    return resp.data
