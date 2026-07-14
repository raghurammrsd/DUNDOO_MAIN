
from app import db
from .models import ReelAd, ReelOrderCharge

def charge_on_order(order_id, shop_id, reel_id=None):
    if not reel_id:
        return
    reel = ReelAd.query.get(reel_id)
    if not reel:
        return
    charge = ReelOrderCharge(
        reel_id=reel_id,
        order_id=order_id,
        shop_id=shop_id,
        charge_amount=5.0
    )
    reel.spent_today += 5.0
    db.session.add(charge)
    db.session.commit()
