
def rank_reels(reels):
    def score(r):
        return ((r.daily_budget - r.spent_today) * 0.4 +
                (1 / (r.radius_km + 0.1)) * 0.4 +
                0.2)
    return sorted(reels, key=score, reverse=True)
