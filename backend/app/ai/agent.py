from flask import session
import re
import urllib.parse

from app.models import Product
from .intent_fast import detect_intent_fast
from .tools import add_product_tool
from .advanced_ai import ask_llm
from .business_advisor import analyze_business


def get_localized_reply(intent_key, lang):
    """Simple dictionary to return localized voice replies (EN, HI, TE)."""
    replies = {
        "user_orders": {
            "en-IN": "Taking you to your orders.",
            "en-US": "Taking you to your orders.",
            "hi-IN": "आपकी ऑर्डर्स पर जा रहे हैं।",
            "te-IN": "మీ ఆర్డర్లకు వెళ్తున్నాము."
        },
        "user_cart": {
            "en-IN": "Opening your cart.",
            "en-US": "Opening your cart.",
            "hi-IN": "आपका कार्ट खोल रहे हैं।",
            "te-IN": "మీ క్రియకు వెళ్తున్నాము."
        },
        "user_track_order": {
            "en-IN": "Your latest order is out for express delivery and will arrive soon.",
            "en-US": "Your latest order is out for express delivery and will arrive soon.",
            "hi-IN": "आपका नवीनतम ऑर्डर एक्सप्रेस डिलीवरी के लिए रास्ते में है और जल्द ही पहुंचेगा।",
            "te-IN": "మీ తాజా ఆర్డర్ డెలివరీ కోసం దారిలో ఉంది మరియు త్వరలో చేరుకుంటుంది."
        },
        "user_reorder": {
            "en-IN": "Opening your previous orders to reorder items into your cart.",
            "en-US": "Opening your previous orders to reorder items into your cart.",
            "hi-IN": "कार्ट में सामान को फिर से ऑर्डर करने के लिए आपके पिछले ऑर्डर खोल रहे हैं।",
            "te-IN": "కార్ట్‌లోకి వస్తువులను మళ్లీ ఆర్డర్ చేయడానికి మీ మునుపటి ఆర్డర్‌లను తెరుస్తున్నాము."
        },
        "user_settings": {
            "en-IN": "Opening settings.",
            "en-US": "Opening settings.",
            "hi-IN": "सेटिंग्स खोल रहे हैं।",
            "te-IN": "సెట్టింగ్‌లను తెరుస్తున్నాము."
        },
        "user_home": {
            "en-IN": "Going back to the dashboard.",
            "en-US": "Going back to the dashboard.",
            "hi-IN": "डैशबोर्ड पर वापस जा रहे हैं।",
            "te-IN": "డాష్‌బోర్డ్‌కు తిరిగి వెళుతున్నాము."
        },
        "user_logout": {
            "en-IN": "Logging out.",
            "en-US": "Logging out.",
            "hi-IN": "लॉग आउट कर रहे हैं।",
            "te-IN": "లాగ్ అవుట్ చేస్తున్నాము."
        },
        "shop_add_product": {
            "en-IN": "Opening the add product page.",
            "en-US": "Opening the add product page.",
            "hi-IN": "उत्पाद जोड़ें पृष्ठ खोल रहे हैं।",
            "te-IN": "ఉత్పత్తిని జోడించండి పేజీని తెరుస్తున్నాము."
        },
        "shop_stock": {
            "en-IN": "Opening your stock inventory.",
            "en-US": "Opening your stock inventory.",
            "hi-IN": "आपकी स्टॉक इन्वेंट्री खोल रहे हैं।",
            "te-IN": "మీ స్టాక్ జాబితాను తెరుస్తున్నాము."
        },
        "shop_billing": {
            "en-IN": "Opening the billing page.",
            "en-US": "Opening the billing page.",
            "hi-IN": "बिलिंग पृष्ठ खोल रहे हैं।",
            "te-IN": "బిల్లింగ్ పేజీని తెరుస్తున్నాము."
        },
        "shop_logout": {
            "en-IN": "Logging out.",
            "en-US": "Logging out.",
            "hi-IN": "लॉग आउट कर रहे हैं।",
            "te-IN": "లాగ్ అవుట్ చేస్తున్నాము."
        },
        "default": {
            "en-IN": "I didn't understand. Please say that again.",
            "en-US": "I didn't understand. Please say that again.",
            "hi-IN": "मुझे समझ नहीं आया। कृपया फिर से कहें।",
            "te-IN": "నాకు అర్థం కాలేదు. దయచేసి మళ్ళీ చెప్పండి."
        }
    }
    # Fallback to English if exact language code not found
    lang_dict = replies.get(intent_key, replies["default"])
    return lang_dict.get(lang, lang_dict.get("en-IN"))


def ask_user_ai(message, lang="en-IN"):
    """Global AI Context Router for Regular Users"""
    message = message.strip()
    text = message.lower()

    if any(word in text for word in ["where is my order", "track", "tracking", "status", "kaha hai", "कहां है", "స్థితి", "ట్రాక్"]):
        return {"reply": get_localized_reply("user_track_order", lang), "action": "/user/my-orders"}
    if any(word in text for word in ["reorder", "repeat", "phir se", "fir se", "మళ్లీ ఆర్డర్", "phir se order"]):
        return {"reply": get_localized_reply("user_reorder", lang), "action": "/user/my-orders"}
    if any(word in text for word in ["order", "orders", "ఆర్డర్", "ఆజ్ఞ", "ऑर्डर", "आदेश", "mera order"]):
        return {"reply": get_localized_reply("user_orders", lang), "action": "/user/my-orders"}
    if any(word in text for word in ["cart", "bag", "basket", "కార్ట్", "సంచి", "బ్యాగ్", "कार्ट", "बैग", "थैला"]):
        return {"reply": get_localized_reply("user_cart", lang), "action": "/user/my-orders"}
    if any(word in text for word in ["setting", "settings", "profile", "సెట్టింగులు", "ప్రొఫైల్", "सेटिंग्स", "प्रोफ़ाइल"]):
        return {"reply": get_localized_reply("user_settings", lang), "action": "/user/settings"}
    if any(word in text for word in ["home", "dashboard", "డాష్బోర్డ్", "హోమ్", "డ్యాష్‌బోర్డ్", "डैशबोर्ड", "होम", "cheyi", "khol"]):
        return {"reply": get_localized_reply("user_home", lang), "action": "/user/dashboard"}
    if any(word in text for word in ["logout", "log out", "sign out", "లాగ్ అవుట్", "लॉग आउट", "बाहर"]):
        return {"reply": get_localized_reply("user_logout", lang), "action": "/user/logout"}

    # If it's none of the rigid UI commands, presume it's a product search query
    # E.g., User says "seb chahiye", we just route them to search page to handle it natively
    encoded_query = urllib.parse.quote(message)
    return {"reply": "Searching the market for you.", "action": f"/user/search?q={encoded_query}"}


def ask_ai(message, lang="en-IN"):

    print("AI RECEIVED:", message)

    # =====================================================
    # FOLLOW-UP MODE (ADD PRODUCT)
    # =====================================================
    if session.get("pending_product"):
        return add_product_tool(message, session)

    intent = detect_intent_fast(message)

    print("DETECTED INTENT:", intent)

    # =====================================================
    # ADD PRODUCT
    # =====================================================
    if intent == "add_product":
        session["pending_product"] = {}
        return add_product_tool(message, session)

    # =====================================================
    # SHOW STOCK
    # =====================================================
    if intent == "show_stock":
        return {
            "reply": get_localized_reply("shop_stock", lang),
            "action": "/shop/stock"
        }

    # =====================================================
    # RECORD SALE (SMART EXTRACTION)
    # =====================================================
    if intent == "record_sale":

        # -------- Extract quantity --------
        qty_match = re.search(r'(\d+)', text)
        quantity = int(qty_match.group(1)) if qty_match else 1

        # -------- Extract customer name --------
        customer_name = ""
        customer_match = re.search(r'for\s+([a-zA-Z ]+)', text)
        if customer_match:
            customer_name = customer_match.group(1).strip().title()

        # -------- Clean product name --------
        cleaned = re.sub(r'\d+\s*kg?', '', text)
        cleaned = re.sub(r'record|sale', '', cleaned)
        cleaned = re.sub(r'for\s+[a-zA-Z ]+', '', cleaned)

        product_name = cleaned.strip()

        print("EXTRACTED PRODUCT:", product_name)

        # -------- Find product in DB --------
        product = Product.query.filter(
            Product.product_name.ilike(f"%{product_name}%"),
            Product.shopkeeper_id == session.get("shop_id")
        ).first()

        if not product:
            return {
                "reply": f"{product_name.title()} not found in your stock."
            }

        return {
            "reply": "Recording sale.",
            "action": "/shop/record-sale",
            "sale_data": {
                "product_id": product.id,
                "quantity": quantity,
                "customer_name": customer_name
            }
        }

    # =====================================================
    # NAVIGATION INTENTS
    # =====================================================
    if intent == "dashboard":
        return {
            "reply": get_localized_reply("user_home", lang),
            "action": "/shop/dashboard"
        }

    if intent == "billing":
        return {
            "reply": get_localized_reply("shop_billing", lang),
            "action": "/shop/billing"
        }

    if intent == "reports":
        return {
            "reply": "Opening reports page.",
            "action": "/shop/reports"
        }

    if intent == "transactions":
        return {
            "reply": "Opening transactions page.",
            "action": "/shop/transactions"
        }

    if intent == "settings":
        return {
            "reply": "Opening settings page.",
            "action": "/shop/settings"
        }

    if intent == "logout":
        session.clear()
        return {
            "reply": get_localized_reply("shop_logout", lang),
            "action": "/shop/login"
        }

    # =====================================================
    # BUSINESS ADVISOR
    # =====================================================
    if intent == "business_advice":
        return {
            "reply": analyze_business()
        }

    # =====================================================
    # ADVANCED AI (LLM)
    # =====================================================
    if intent in [
        "marketing_suggestion",
        "pricing_suggestion",
        "revenue_prediction"
    ]:
        return {
            "reply": ask_llm(message)
        }

    # =====================================================
    # DEFAULT RESPONSE
    # =====================================================
    return {
        "reply": "How can I help you with your shop today?"
    }