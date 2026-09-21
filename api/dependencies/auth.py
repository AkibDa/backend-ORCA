from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import jwt
from jwt import PyJWKClient
import contextvars

from backend.core.config import settings

current_token = contextvars.ContextVar("current_token", default=None)

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_jwks_url() -> str:
    # Ensure no trailing slash
    base_url = settings.SUPABASE_URL.rstrip('/')
    return f"{base_url}/auth/v1/.well-known/jwks.json"

_jwks_client = None

def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(get_jwks_url())
    return _jwks_client

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            options={"verify_exp": True}
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Only set the token in context if validation completely succeeds
        current_token.set(token)
        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Validation failed: Signature has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"JWT Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
