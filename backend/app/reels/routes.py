from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import os, uuid

from app import db
from .models import ReelAd
from .service import get_eligible_reels
from .ranker import rank_reels
from math import radians, sin, cos, sqrt, asin
from app.utils.storage import upload_video

reels_bp = Blueprint("reels", __name__)

# -----------------------------
# Helpers
# -----------------------------
def allowed_video(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]
    )


# -----------------------------
# CREATE REEL (SHOPKEEPER)
# -----------------------------
@reels_bp.route("/shopkeeper/reels", methods=["POST"])
def create_reel():
    shop_id = session.get("shop_id")
    if not shop_id:
        return {"error": "Unauthorized"}, 401

    video = request.files.get("video")
    if not video or video.filename == "":
        return {"error": "Video file required"}, 400

    # Extension check
    if not allowed_video(video.filename):
        return {"error": "Invalid video format"}, 400

    # MIME type check (extra safety)
    if video.mimetype not in ("video/mp4", "video/webm", "video/quicktime"):
        return {"error": "Unsupported video type"}, 400

    video_url = upload_video(video, folder="dundoo/reels", prefix=f"{shop_id}_{uuid.uuid4().hex}")

    days = int(request.form.get("duration_days", 3))

    reel = ReelAd(
        shop_id=shop_id,
        video_url=video_url,
        offer_type=request.form.get("offer_type"),
        offer_value=request.form.get("offer_value"),
        latitude=float(request.form.get("lat")),
        longitude=float(request.form.get("lon")),
        radius_km=float(request.form.get("radius", 40)),
        daily_budget=float(request.form.get("budget", 100)),
        expires_at=datetime.utcnow() + timedelta(days=days),
        is_active=True
    )

    db.session.add(reel)
    db.session.commit()

    return jsonify({"status": "reel_created"}), 201


def calculate_distance(lat1, lng1, lat2, lng2):
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return None

    lat1 = float(lat1)
    lng1 = float(lng1)
    lat2 = float(lat2)
    lng2 = float(lng2)

    rlat1 = radians(lat1)
    rlng1 = radians(lng1)
    rlat2 = radians(lat2)
    rlng2 = radians(lng2)

    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1

    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
    c = 2 * asin(sqrt(a))
    R = 6371.0

    return R * c


# -----------------------------
# USER REELS FEED (PUBLIC)
# -----------------------------
@reels_bp.route("/api/reels", methods=["GET"])

def user_reels():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    reels = ReelAd.query.filter_by(is_active=True).all()

    filtered = []

    for r in reels:
        if not r.latitude or not r.longitude:
            continue

        distance = calculate_distance(lat, lon, r.latitude, r.longitude)

        if distance <= 60:   # 🔥 60 KM FILTER
            filtered.append({
                "reel_id": r.id,
                "video": r.video_url,
                "offer": r.offer_value,
                "shop_id": r.shop_id
            })

    return jsonify(filtered)

# -----------------------------
# SHOPKEEPER: MY REELS
# -----------------------------
@reels_bp.route("/shopkeeper/my-reels", methods=["GET"])
def my_reels():
    shop_id = session.get("shop_id")
    if not shop_id:
        return {"error": "Unauthorized"}, 401

    reels = (
        ReelAd.query
        .filter_by(shop_id=shop_id)
        .order_by(ReelAd.created_at.desc())
        .all()
    )

    now = datetime.utcnow()

    return jsonify([
        {
            "id": r.id,
            "video": r.video_url,
            "offer": (
                "Buy 1 Get 1"
                if r.offer_type == "bogo"
                else f"{r.offer_value}{'%' if r.offer_type == 'percent' else ''} OFF"
            ),
            "days_left": max((r.expires_at - now).days, 0) if r.expires_at else 0,
            "active": r.is_active and (not r.expires_at or r.expires_at >= now)
        }
        for r in reels
    ])


# -----------------------------
# DELETE / STOP REEL
# -----------------------------
@reels_bp.route("/shopkeeper/reels/<int:reel_id>", methods=["DELETE"])
def delete_reel(reel_id):
    shop_id = session.get("shop_id")
    if not shop_id:
        return {"error": "Unauthorized"}, 401

    reel = (
        ReelAd.query
        .filter_by(id=reel_id, shop_id=shop_id)
        .first_or_404()
    )

    reel.is_active = False
    db.session.commit()

    return jsonify({"status": "deleted"}), 200
