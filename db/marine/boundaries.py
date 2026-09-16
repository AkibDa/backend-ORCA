from typing import List, Dict, Any
from backend.db.client import get_supabase_client
from backend.db.marine.db_reliability import with_db_reliability

@with_db_reliability(max_retries=2)
def get_all_boundaries() -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = client.table("marine_boundaries").select("*").execute()
    return resp.data

@with_db_reliability(max_retries=2)
def check_point_in_boundaries(lat: float, lon: float) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    # Assuming an RPC `check_point_in_marine_boundaries` exists for PostGIS spatial queries
    # which uses ST_Contains or ST_Intersects
    resp = client.rpc("check_point_in_marine_boundaries", {
        "p_lat": lat,
        "p_lon": lon
    }).execute()
    return resp.data
