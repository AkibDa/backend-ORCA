from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseWeatherProvider(ABC):
    @abstractmethod
    def fetch_weather(self, lat: float, lon: float, target_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        pass

class BaseOceanProvider(ABC):
    @abstractmethod
    def fetch_ocean(self, lat: float, lon: float, target_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        pass

class BasePFZProvider(ABC):
    @abstractmethod
    def fetch_pfz(self, lat: float, lon: float, target_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        pass
