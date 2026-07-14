import re

def detect_intent_fast(text):
    text = text.lower().strip()

    # DASHBOARD
    if any(word in text for word in ["dashboard", "home", "main", "డాష్బోర్డ్", "హోమ్", "డ్యాష్‌బోర్డ్", "डैशबोर्ड", "होम", "cheyi", "khol"]):
        return "dashboard"

    # STOCK
    if any(word in text for word in ["stock", "inventory", "స్టాక్", "ఇన్వెంటరీ", "स्टॉक", "इन्वेंटरी"]):
        return "show_stock"

    # REPORTS
    if any(word in text for word in ["report", "reports", "analysis", "రిపోర్ట్", "విశ్లేషణ", "रिपोर्ट", "विश्लेषण"]):
        return "reports"

    # SALE
    if any(word in text for word in ["sale", "sell", "record", "అమ్మకం", "అమ్మండి", "बिक्री", "बेचना"]):
        return "record_sale"

    # BILLING
    if any(word in text for word in ["bill", "invoice", "billing", "బిల్లు", "ఇన్వాయిస్", "बिल", "इनवॉइस"]):
        return "billing"

    # TRANSACTIONS
    if any(word in text for word in ["transaction", "transactions", "payment", "లావాదేవీలు", "చెల్లింపు", "लेन-देन", "भुगतान"]):
        return "transactions"

    # SETTINGS
    if any(word in text for word in ["setting", "settings", "profile", "సెట్టింగులు", "ప్రొఫైల్", "सेटिंग्स", "प्रोफ़ाइल"]):
        return "settings"

    # LOGOUT
    if any(word in text for word in ["logout", "sign out", "లాగ్ అవుట్", "लॉग आउट", "बाहर"]):
        return "logout"

    # BUSINESS ANALYSIS
    if any(word in text for word in ["analyze", "business", "advice", "సలహా", "व्यापार", "सलाह"]):
        return "business_advice"

    # ADD PRODUCT
    if any(word in text for word in ["add", "create", "naya", "new", "kotha", "జోడించు", "క్రొత్త", "జోడించండి", "नया", "जोड़ें", "plus"]):
        return "add_product"

    return "general"