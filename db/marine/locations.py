from typing import List, Dict, Any
from backend.db.client import get_supabase_client
from backend.db.marine.db_reliability import with_db_reliability

@with_db_reliability(max_retries=2)
def search_locations_by_name(name: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    # Using ilike for case-insensitive search
    resp = client.table("locations").select("*").ilike("name", f"%{name}%").execute()
    return resp.data

@with_db_reliability(max_retries=2)
def get_location_by_id(location_id: int) -> Dict[str, Any] | None:
    client = get_supabase_client()
    resp = client.table("locations").select("*").eq("id", location_id).execute()
    return resp.data[0] if resp.data else None
