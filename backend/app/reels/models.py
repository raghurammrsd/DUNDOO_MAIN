from datetime import datetime
from app import db

class ReelAd(db.Model):
    __tablename__ = "reel_ads"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, nullable=False)
    video_url = db.Column(db.String(255), nullable=False)

    offer_type = db.Column(db.String(20))     # percent / flat / bogo
    offer_value = db.Column(db.String(50))    # 20 / ₹50 / Free Item

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_km = db.Column(db.Float, default=1.0)

    daily_budget = db.Column(db.Float, default=100.0)
    spent_today = db.Column(db.Float, default=0.0)

    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReelOrderCharge(db.Model):
    __tablename__ = "reel_order_charges"

    id = db.Column(db.Integer, primary_key=True)
    reel_id = db.Column(db.Integer)
    order_id = db.Column(db.Integer)
    shop_id = db.Column(db.Integer)
    charge_amount = db.Column(db.Float, default=5.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
