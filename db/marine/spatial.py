import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_bounding_box(lat, lon, radius_km):
    # Rough approximation: 1 deg lat = 111km, 1 deg lon = 111km * cos(lat)
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    return (lat - lat_delta, lat + lat_delta, lon - lon_delta, lon + lon_delta)
