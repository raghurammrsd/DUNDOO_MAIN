from flask import Blueprint, request, jsonify
from app.shop.routes import _get_logged_in_shop
from .agent import ask_ai, ask_user_ai

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@ai_bp.route("/chat", methods=["POST"])
def chat():

    shop = _get_logged_in_shop()
    if not shop:
        return jsonify({
            "reply": "Please login as shopkeeper first."
        }), 401

    message = request.json.get("message", "")
    lang = request.json.get("lang", "en-IN")

    print("SHOP AI RECEIVED:", message)   # debug

    reply = ask_ai(message, lang=lang)
    print("SHOP AI RESPONSE:", reply)

    if isinstance(reply, dict):
        return jsonify(reply)

    return jsonify({"reply": reply})

@ai_bp.route("/user_chat", methods=["POST"])
def user_chat():
    message = request.json.get("message", "")
    lang = request.json.get("lang", "en-IN")
    
    print("USER AI RECEIVED:", message, "LANG:", lang)   # debug
    reply = ask_user_ai(message, lang=lang)
    print("USER AI RESPONSE:", reply)

    if isinstance(reply, dict):
        return jsonify(reply)

    return jsonify({"reply": reply})