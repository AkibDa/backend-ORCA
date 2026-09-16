from typing import Optional, Any
import logging
from backend.core.config import settings
from .base import BaseWeatherProvider, BaseOceanProvider, BasePFZProvider
from .reliability import with_reliability

logger = logging.getLogger(__name__)

def wrap_provider_method(provider: Any, method_name: str, provider_name: str) -> Any:
    if provider is None:
        return None
    original_method = getattr(provider, method_name)
    wrapped_method = with_reliability(provider_name, settings.PROVIDER_MAX_RETRIES)(original_method)
    setattr(provider, method_name, wrapped_method)
    return provider

def get_weather_provider() -> Optional[BaseWeatherProvider]:
    provider_type = settings.WEATHER_PROVIDER.lower()
    if provider_type == "disabled":
        return None
    # Future government APIs or other providers will be registered here
    # e.g., if provider_type == "imd": provider = IMDWeatherProvider()
    # return wrap_provider_method(provider, "fetch_weather", "weather")
    logger.warning(f"Unknown WEATHER_PROVIDER: {provider_type}. Returning None.")
    return None

def get_ocean_provider() -> Optional[BaseOceanProvider]:
    provider_type = settings.OCEAN_PROVIDER.lower()
    if provider_type == "disabled":
        return None
    logger.warning(f"Unknown OCEAN_PROVIDER: {provider_type}. Returning None.")
    return None

def get_pfz_provider() -> Optional[BasePFZProvider]:
    provider_type = settings.PFZ_PROVIDER.lower()
    if provider_type == "disabled":
        return None
    logger.warning(f"Unknown PFZ_PROVIDER: {provider_type}. Returning None.")
    return None

