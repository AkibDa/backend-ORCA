import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings(BaseSettings):
    PROJECT_NAME: str = "ORCA Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # External Data Providers
    WEATHER_PROVIDER: str = os.getenv("WEATHER_PROVIDER", "disabled")
    OCEAN_PROVIDER: str = os.getenv("OCEAN_PROVIDER", "disabled")
    PFZ_PROVIDER: str = os.getenv("PFZ_PROVIDER", "disabled")
    
    # Freshness / TTL Constraints
    WEATHER_DATA_MAX_AGE_HOURS: int = int(os.getenv("WEATHER_DATA_MAX_AGE_HOURS", "6"))
    OCEAN_DATA_MAX_AGE_HOURS: int = int(os.getenv("OCEAN_DATA_MAX_AGE_HOURS", "6"))
    
    # Network
    PROVIDER_TIMEOUT_SECONDS: float = float(os.getenv("PROVIDER_TIMEOUT_SECONDS", "2.5"))
    PROVIDER_MAX_RETRIES: int = int(os.getenv("PROVIDER_MAX_RETRIES", "2"))
    ORCA_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("ORCA_REQUEST_TIMEOUT_SECONDS", "15.0"))
    
    # Rate Limiting & Protection (Phase 4G)
    ORCA_RATE_LIMIT_REQUESTS: int = int(os.getenv("ORCA_RATE_LIMIT_REQUESTS", "30"))
    ORCA_RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("ORCA_RATE_LIMIT_WINDOW_SECONDS", "60"))
    ORCA_MAX_CONCURRENT_REQUESTS: int = int(os.getenv("ORCA_MAX_CONCURRENT_REQUESTS", "4"))
    
    # Command Center (Hackathon Prototype)
    ORCA_COMMAND_CENTER_ENABLED: bool = os.getenv("ORCA_COMMAND_CENTER_ENABLED", "false").lower() == "true"
    ORCA_COMMAND_CENTER_ORIGIN: str = os.getenv("ORCA_COMMAND_CENTER_ORIGIN", "http://localhost:5173")


settings = Settings()

MODEL_BACKEND = os.getenv("ORCA_MODEL_BACKEND", "cuda").lower()

if MODEL_BACKEND not in {"cuda", "mlx", "cpu"}:
    raise RuntimeError(
        "ORCA_MODEL_BACKEND must be 'cuda', 'mlx', or 'cpu'. " f"Got: {MODEL_BACKEND!r}"
    )
