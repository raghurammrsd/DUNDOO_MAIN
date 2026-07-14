from math import radians, sin, cos, asin, sqrt

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from sqlalchemy import func
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
import razorpay
from flask import current_app

from app.models import User, Product, Shopkeeper, Order, Wishlist, FavoriteShop, Review
from app.otp_utils import (
    is_valid_email,
    start_otp_flow,
    verify_otp,
    get_current_record,
)

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("user.register"))

        if not is_valid_email(email):
            flash("Enter a valid email.", "danger")
            return redirect(url_for("user.register"))

        
        try:
            existing_username = User.query.filter(
                func.lower(User.username) == username.lower()
            ).first()
        except Exception as e:
            db.session.rollback()
            if hasattr(db, "engine"):
                db.engine.dispose()
            existing_username = User.query.filter(
                func.lower(User.username) == username.lower()
            ).first()

        if existing_username:
            flash("Username already exists.", "danger")
            return redirect(url_for("user.register"))

        try:
            existing_email = User.query.filter(
                func.lower(User.email) == email.lower()
            ).first()
        except Exception as e:
            db.session.rollback()
            if hasattr(db, "engine"):
                db.engine.dispose()
            existing_email = User.query.filter(
                func.lower(User.email) == email.lower()
            ).first()

        if existing_email:
            flash("This email is already used for another user account.", "danger")
            return redirect(url_for("user.register"))

        hashed = generate_password_hash(password)

        payload = {
            "username": username,
            "email": email,
            "phone": phone,
            "password_hash": hashed,
        }

        start_otp_flow(
            context="user_register",
            email=email,
            name=username,
            payload=payload,
        )

        flash("OTP sent to your email.", "info")
        return redirect(url_for("user.verify_otp_view"))

    return render_template("user/register.html")



@user_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp_view():
    record = get_current_record()

    if not record or record.context != "user_register":
        flash("No OTP session found. Register again.", "warning")
        return redirect(url_for("user.register"))

    if request.method == "POST":
        code = (request.form.get("otp") or "").strip()

        ok, data = verify_otp(code, expected_context="user_register")

        if not ok:
            flash(data, "danger")
            return redirect(url_for("user.verify_otp_view"))

        payload = data.get("payload", {})
        username = payload.get("username")
        email = payload.get("email")
        phone = payload.get("phone")
        password_hash = payload.get("password_hash")

        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password_hash=password_hash,
            email_verified=True,
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Login now.", "success")
            return redirect(url_for("user.login"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user account: {e}")
            flash("An error occurred during account creation. Please try again.", "danger")
            return redirect(url_for("user.verify_otp_view"))

    return render_template(
        "auth/verify_otp.html",
        email=record.email,
        role="user",
    )




@user_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("user.login"))

        if not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("user.login"))

        login_user(user)
        flash("Welcome!", "success")
        return redirect(url_for("user.dashboard"))

    return render_template("user/login.html")



@user_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("user.login"))




@user_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "user/dashboard.html",
        user=current_user,
    )




def calc_distance(lat1, lng1, lat2, lng2):
    """
    Haversine distance in kilometers.
    Returns None if any coord is None.
    """
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return None

    
    
    try:
        lat1 = float(lat1)
        lng1 = float(lng1)
        lat2 = float(lat2)
        lng2 = float(lng2)
    except (TypeError, ValueError):
        return None

    
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



@user_bp.route("/api/validate_coupon", methods=["POST"])
def validate_coupon():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip().upper()
    subtotal = float(data.get("subtotal", 0))

    if not code:
        return jsonify({"success": False, "message": "Please enter a promo code"})

    if code == "WELCOME50":
        if subtotal < 100:
            return jsonify({"success": False, "message": "Minimum cart value ₹100 required for WELCOME50"})
        return jsonify({"success": True, "discount": 50, "message": "🎉 ₹50 discount applied!"})
    elif code == "DUNDOO10":
        discount = round(subtotal * 0.10)
        return jsonify({"success": True, "discount": discount, "message": f"🎉 10% discount (₹{discount}) applied!"})
    elif code == "VOICEAI":
        return jsonify({"success": True, "discount": 30, "message": "🤖 AI Special: ₹30 discount applied!"})
    else:
        return jsonify({"success": False, "message": "Invalid or expired promo code"})


@user_bp.route("/api/search_products_nearby", methods=["POST"])
@login_required
def search_products_nearby():
    """
    Expects JSON:
      - query
      - latitude, longitude  (user)
      - min_distance_km, max_distance_km
    """
    data = request.get_json() or {}

    query = (data.get("query") or "").strip()
    user_lat = data.get("latitude")
    user_lng = data.get("longitude")

    min_km = data.get("min_distance_km", 0)
    max_km = data.get("max_distance_km", 10)

    try:
        min_km = float(min_km)
    except (TypeError, ValueError):
        min_km = 0.0
    try:
        max_km = float(max_km)
    except (TypeError, ValueError):
        max_km = 10.0

    if user_lat is None or user_lng is None:
        return jsonify({"products": [], "error": "Missing user location"}), 200

    try:
        user_lat = float(user_lat)
        user_lng = float(user_lng)
    except (TypeError, ValueError):
        return jsonify({"products": [], "error": "Invalid user location"}), 200

    
    session["user_lat"] = user_lat
    session["user_lng"] = user_lng

    # --- Phase 4 & 5: Multi-lingual Local AI Parsing ---
    # Strip common conversational AI filler words to find the core product
    fillers = [
        "i", "want", "find", "show", "me", "some", "need", "to", "chahiye",
        "muze", "mujhe", "kavali", "naaku", "undha", "hai", "kya", "get", "buy",
        "looking", "for", "search", "product", "products", "item", "items",
        "please", "can", "you", "a", "an", "the"
    ]
    search_terms = query.lower().split()
    clean_terms = [t for t in search_terms if t not in fillers]
    
    # If the user only spoke filler words (e.g. "I want it"), fallback to the full query
    parsed_query = " ".join(clean_terms) if clean_terms else query.lower()

    # Built-in Local Synonym Engine (No API required)
    # Maps Hindi/Telugu/Slang -> English DB products
    synonyms = {
        "apple": ["सेब", "seb", "ఆపిల్", "aalu", "aapu", "apples", "apple"],
        "milk": ["दूध", "paalu", "palu", "doodh", "dudh", "milks", "milk"],
        "bread": ["abroti", "roti", "bisket", "breads", "bread"],
        "rice": ["chawal", "biyyam", "chaval", "chaaval", "rices", "rice"],
        "water": ["pani", "neelu", "paani", "neellu", "waters", "water"],
        "sugar": ["cheeni", "shakkar", "chakkera", "sugar"],
        "onion": ["pyaaz", "ullipaya", "ulli", "onions", "onion"],
        "tomato": ["tamatar", "tamata", "tomatoes", "tomato"],
        "mango": ["aam", "maamidi", "mamidi", "mangoes", "mango"]
    }

    # Reverse lookup the cleaned terms to see if it matches any regional/plural synonym
    db_search_key = parsed_query
    for eng_term, regional_list in synonyms.items():
        # Match whole words to prevent 'seb' from matching inside 'something else'
        if any(reg_term in clean_terms for reg_term in regional_list):
            db_search_key = eng_term
            break

    q = (
        db.session.query(Product, Shopkeeper)
        .join(Shopkeeper, Product.shopkeeper_id == Shopkeeper.id)
        .filter(Product.available.is_(True))
    )

    if query:
        # Search against both the original query and the translated synonym
        q = q.filter((Product.product_name.ilike(f"%{query}%")) | (Product.product_name.ilike(f"%{db_search_key}%")))

    results = []

    for product, shop in q.all():
        
        if shop.latitude is None or shop.longitude is None:
            continue

        dist = calc_distance(user_lat, user_lng, shop.latitude, shop.longitude)
        if dist is None:
            continue

        if dist < min_km or dist > max_km:
            continue

        results.append(
            {
                "product_id": product.id,
                "product_name": product.product_name,
                "category": product.category or "Grocery",
                "description": product.description or "",
                "price": float(product.price) if product.price is not None else None,
                "available": product.available,
                "shop_id": shop.id,
                "shop_name": shop.shop_name,
                "address": shop.address,
                "pincode": shop.pincode,
                "landmark": shop.landmark or "",
                "distance_km": round(dist, 2),
                "image_url": product.image_url,
            }
        )

    results.sort(key=lambda x: x["distance_km"])

    return jsonify({"products": results})






@user_bp.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    shop = product.shop  
    

    user_lat = session.get("user_lat")
    user_lng = session.get("user_lng")

    return render_template(
        "user/product_detail.html",
        product=product,
        shop=shop,
        user_lat=user_lat,
        user_lng=user_lng,
    )





@user_bp.route("/search")
@login_required
def search():
    return render_template("user/search.html")


@user_bp.route("/nearby")
@login_required
def nearby():
    return render_template("user/search.html")


@user_bp.route("/add-to-cart/<int:product_id>")
@login_required
def add_to_cart(product_id):
    print("ADD TO CART CLICKED")
    print("USER:", current_user.id)
    print("PRODUCT:", product_id)

    product = Product.query.get_or_404(product_id)

    order = Order(
        user_id=current_user.id,
        product_id=product.id,
        shop_id=product.shopkeeper_id,
        price=product.price,
        quantity=1,
        status="Placed"
    )

    db.session.add(order)
    db.session.commit()

    print("ORDER SAVED")

    return redirect(url_for("user.my_orders"))


@user_bp.route("/cart")
@login_required
def cart():
    return render_template("user/cart.html", active_page="cart")

@user_bp.route("/api/cart/checkout", methods=["POST"])
@login_required
def checkout_cart_api():
    data = request.get_json() or {}
    items = data.get("items") or []
    created_count = 0
    for item in items:
        pid = item.get("id")
        qty = item.get("qty", 1)
        try:
            pid_int = int(pid)
        except (ValueError, TypeError):
            continue
        product = Product.query.get(pid_int)
        if product:
            order = Order(
                user_id=current_user.id,
                product_id=product.id,
                shop_id=product.shopkeeper_id,
                price=float(product.price or 0),
                quantity=int(qty),
                status="Placed"
            )
            db.session.add(order)
            created_count += 1
    if created_count > 0:
        db.session.commit()
    return jsonify({"success": True, "count": created_count})


@user_bp.route("/my-orders")
@login_required
def my_orders():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template("user/my_orders.html", orders=orders)




@user_bp.route("/create-payment", methods=["POST"])
@login_required
def create_payment():
    client = razorpay.Client(
        auth=(
            current_app.config["RAZORPAY_KEY_ID"],
            current_app.config["RAZORPAY_KEY_SECRET"],
        )
    )

    orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Placed"
    ).all()

    total = sum(float(o.price) * o.quantity for o in orders)

    razorpay_order = client.order.create({
        "amount": int(total * 100),  # paise
        "currency": "INR",
        "payment_capture": 1
    })

    return {
        "order_id": razorpay_order["id"],
        "amount": razorpay_order["amount"]
    }


@user_bp.route("/payment-success")
@login_required
def payment_success():
    Order.query.filter_by(
        user_id=current_user.id,
        status="Placed"
    ).update({"status": "Paid"})

    db.session.commit()
    return render_template("user/payment_success.html")


@user_bp.route("/reels")
def reels():
    return render_template(
        "user/reels.html",
        active_page="reels"
    )

@user_bp.route("/api/smart_categories")
def smart_categories():
    return jsonify({"categories": ["Groceries", "Fruits", "Vegetables", "Dairy", "Snacks", "Beverages"]})

@user_bp.route("/api/daily_deals")
def daily_deals():
    return jsonify({"deals": [
        {"product_name": "Farm Fresh Milk 1L", "shop_name": "Daily Needs", "discount_percentage": 20, "original_price": 60, "discounted_price": 48, "image_url": ""},
        {"product_name": "Organic Tomatoes 1kg", "shop_name": "Green Grocers", "discount_percentage": 15, "original_price": 40, "discounted_price": 34, "image_url": ""}
    ]})

@user_bp.route("/api/recommendations")
def recommendations():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    products = Product.query.filter_by(available=True).limit(4).all()
    res = []
    for p in products:
        shop = p.shop
        dist = calc_distance(lat, lng, shop.latitude, shop.longitude) if lat and lng and shop.latitude and shop.longitude else 2.5
        res.append({
            "product_name": p.product_name,
            "shop_name": shop.shop_name,
            "distance_km": round(dist or 0, 1),
            "price": p.price,
            "image_filename": p.display_image
        })
    return jsonify({"recommendations": res})

@user_bp.route("/api/trending")
def trending():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    products = Product.query.filter_by(available=True).order_by(Product.id.desc()).limit(4).all()
    res = []
    for p in products:
        shop = p.shop
        dist = calc_distance(lat, lng, shop.latitude, shop.longitude) if lat and lng and shop.latitude and shop.longitude else 1.2
        res.append({
            "product_name": p.product_name,
            "shop_name": shop.shop_name,
            "distance_km": round(dist or 0, 1),
            "price": p.price,
            "image_filename": p.display_image
        })
    return jsonify({"trending": res})

@user_bp.route("/api/nearby_shops_discovery")
def nearby_shops_discovery():
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    shops = Shopkeeper.query.limit(5).all()
    res = []
    for s in shops:
        dist = calc_distance(lat, lng, s.latitude, s.longitude) if lat and lng and s.latitude and s.longitude else 3.0
        res.append({
            "shop_name": s.shop_name,
            "rating": 4.8,
            "distance_km": round(dist or 0, 1),
        })
    return jsonify({"shops": res})

@user_bp.route("/transactions")
@login_required
def transactions():
    # Mocking transactions for UI demonstration
    mock_transactions = [
        {"id": "TXN9842A", "date": "10-Oct-2026", "amount": 450.00, "status": "Success"},
        {"id": "TXN8732B", "date": "08-Oct-2026", "amount": 1250.50, "status": "Success"},
        {"id": "TXN1120X", "date": "01-Oct-2026", "amount": 90.00, "status": "Failed"}
    ]
    return render_template("user/transactions.html", transactions=mock_transactions)

@user_bp.route("/settings")
@login_required
def settings():
    return render_template("user/settings.html", user=current_user)

@user_bp.route("/api/search/suggestions")
def search_suggestions():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"suggestions": []})
    prods = Product.query.filter(Product.product_name.ilike(f"%{q}%")).limit(6).all()
    shops = Shopkeeper.query.filter(Shopkeeper.shop_name.ilike(f"%{q}%")).limit(3).all()
    sugs = list(set([p.product_name for p in prods] + [s.shop_name for s in shops]))
    return jsonify({"suggestions": sugs[:8]})

@user_bp.route("/wishlist")
def wishlist():
    items = []
    if current_user.is_authenticated:
        w_records = Wishlist.query.filter_by(user_id=current_user.id).all()
        items = [w.product for w in w_records if w.product]
    return render_template("user/wishlist.html", wishlist_items=items)

@user_bp.route("/wishlist/toggle", methods=["POST"])
def wishlist_toggle():
    data = request.get_json() or {}
    pid = data.get("product_id")
    if not pid or not current_user.is_authenticated:
        return jsonify({"success": True})
    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=pid))
    db.session.commit()
    return jsonify({"success": True})

@user_bp.route("/shop/favorite/toggle", methods=["POST"])
def favorite_shop_toggle():
    data = request.get_json() or {}
    sid = data.get("shopkeeper_id")
    if not sid or not current_user.is_authenticated:
        return jsonify({"success": True})
    existing = FavoriteShop.query.filter_by(user_id=current_user.id, shopkeeper_id=sid).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(FavoriteShop(user_id=current_user.id, shopkeeper_id=sid))
    db.session.commit()
    return jsonify({"success": True})

@user_bp.route("/api/review/submit", methods=["POST"])
def review_submit():
    if not current_user.is_authenticated:
        return jsonify({"success": False, "message": "Login required"}), 401
    data = request.get_json() or {}
    try:
        pid = int(data.get("product_id"))
    except (ValueError, TypeError):
        pid = None
    try:
        sid = int(data.get("shopkeeper_id"))
    except (ValueError, TypeError):
        sid = None
    try:
        rating = int(data.get("rating") or 5)
    except (ValueError, TypeError):
        rating = 5
    comment = (data.get("comment") or "").strip()
    if not comment:
        return jsonify({"success": False, "message": "Comment cannot be empty"})
    rev = Review(user_id=current_user.id, product_id=pid, shopkeeper_id=sid, rating=rating, comment=comment)
    db.session.add(rev)
    db.session.commit()
    return jsonify({"success": True, "message": "Review added successfully!"})


@user_bp.route("/categories")
@login_required
def categories():
    return render_template("user/categories.html", active_page="categories")


@user_bp.route("/buy-again")
@login_required
def buy_again():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    products = [o.product for o in orders if o.product]
    seen = set()
    unique_products = []
    for p in products:
        if p.id not in seen:
            seen.add(p.id)
            unique_products.append(p)
    return render_template("user/buy_again.html", active_page="buy_again", products=unique_products)


@user_bp.route("/recent-views")
@login_required
def recent_views():
    return render_template("user/recent_views.html", active_page="recent_views")


@user_bp.route("/offers")
@login_required
def offers():
    return render_template("user/offers.html", active_page="offers")

