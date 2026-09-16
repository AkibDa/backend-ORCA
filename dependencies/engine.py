import sys
from pathlib import Path


PROTO_DIR = Path(__file__).resolve().parents[2] / "Proto"

if str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))


from orchestrator.engine import OrcaOrchestrator
from agents.weather.agent import WeatherAgent
from agents.ocean.agent import OceanAgent
from agents.ocean_state.agent import OceanStateAgent
from agents.tide.agent import TideAgent
from agents.pfz.agent import PFZAgent
from agents.geospatial.agent import GeospatialAgent
from agents.risk.agent import RiskAgent
from agents.productivity.agent import FishProductivityAgent
from agents.rules.safety_agent import SafetyRuleAgent
from agents.rules.recommendation_agent import RecommendationAgent
from agents.marine_safety.agent import MarineSafetyAgent


def create_orca_engine() -> OrcaOrchestrator:
    """Create the complete ORCA agent registry once at application startup."""
    
    # Pre-warm all ML models synchronously to avoid initialization races during concurrent execution
    try:
        from agents.weather.model import get_weather_model
        from agents.pfz.model import get_pfz_model
        from agents.ocean.model import get_ocean_suitability_model
        from agents.risk.model import get_marine_risk_model
        
        get_weather_model()
        get_pfz_model()
        get_ocean_suitability_model()
        get_marine_risk_model()
    except Exception as e:
        print(f"Warning: Failed to pre-warm models: {e}")
        
    registry = {
        "weather": WeatherAgent(),
        "ocean": OceanAgent(),
        "ocean_state": OceanStateAgent(),
        "tide": TideAgent(),
        "pfz": PFZAgent(),
        "geospatial": GeospatialAgent(),
        "risk": RiskAgent(),
        "productivity": FishProductivityAgent(),
        "marine_safety": MarineSafetyAgent(),
        "safety_rules": SafetyRuleAgent(),
        "recommendation": RecommendationAgent()
    }
    return OrcaOrchestrator(registry=registry)
