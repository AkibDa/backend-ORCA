# pyrefly: ignore [missing-import]
from supabase import create_client, Client, ClientOptions
from backend.core.config import settings

_supabase_client = None

def get_supabase_client() -> Client:
    # Do not use global _supabase_client if we have request-specific auth
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")
    
    options = ClientOptions(postgrest_client_timeout=3.0)
    
    # Try to get the current JWT from the contextvar
    from backend.api.dependencies.auth import current_token
    token = current_token.get()
    
    if token:
        # In recent versions of supabase-py, passing it in headers is supported and preferred
        options.headers.update({"Authorization": f"Bearer {token}"})
        
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options=options)
    
    if token:
        # Fallback to older method just in case
        try:
            client.postgrest.auth(token)
        except Exception:
            pass
            
    return client
