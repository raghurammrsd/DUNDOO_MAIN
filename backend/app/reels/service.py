
import math
from .models import ReelAd

def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_eligible_reels(user_lat, user_lon):
    reels = ReelAd.query.filter_by(is_active=True).all()
    eligible = []
    for r in reels:
        if r.spent_today >= r.daily_budget:
            continue
        if distance_km(user_lat, user_lon, r.latitude, r.longitude) <= r.radius_km:
            eligible.append(r)
    return eligible
