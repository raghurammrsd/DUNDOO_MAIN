import os, time
from datetime import datetime, date, timedelta
from collections import defaultdict
from io import BytesIO
import uuid

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app, send_file
)
from sqlalchemy import func
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app import db
from app.models import Shopkeeper, Product, Sale, StockMovement, Expense, OnlineTransaction, Order
import razorpay
from app.otp_utils import (
    is_valid_email, start_otp_flow, verify_otp,
    get_current_record, send_inventory_email
)
from app.utils.storage import upload_image

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")
def get_razorpay_client():
    return razorpay.Client(auth=(
        current_app.config["RAZORPAY_KEY_ID"],
        current_app.config["RAZORPAY_KEY_SECRET"]
    ))


def _get_logged_in_shop():
    sid = session.get("shop_id")
    if not sid:
        return None
    return Shopkeeper.query.get(sid)


def _send_inventory_alert_email(shop, subject, lines):
    if not lines:
        return
    body = "\n".join(lines)
    try:
        send_inventory_email(shop.email, subject, body)
    except Exception as e:
        current_app.logger.error("Inventory mail error: %s", e)


@shop_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        shop_name = request.form.get("shop_name", "").strip()
        shopkeeper_name = request.form.get("shopkeeper_name", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        pincode = request.form.get("pincode", "").strip()
        landmark = request.form.get("landmark", "").strip()

        lat_raw = request.form.get("latitude", "").strip()
        lng_raw = request.form.get("longitude", "").strip()

        if not all([shop_name, shopkeeper_name, email, address, pincode]):
            flash("All fields are required.", "danger")
            return redirect(url_for("shop.register"))

        if not lat_raw or not lng_raw:
            flash("Click 'Use current location' and set your shop pin.", "danger")
            return redirect(url_for("shop.register"))

        try:
            latitude = float(lat_raw)
            longitude = float(lng_raw)
        except ValueError:
            flash("Invalid location data. Try again.", "danger")
            return redirect(url_for("shop.register"))

        new_shop = Shopkeeper(
            shop_name=shop_name,
            shopkeeper_name=shopkeeper_name,
            email=email,
            address=address,
            pincode=pincode,
            landmark=landmark or None,
            latitude=latitude,
            longitude=longitude
        )

        db.session.add(new_shop)
        db.session.commit()

        flash("Shop registered successfully. Login with OTP.", "success")
        return redirect(url_for("shop.login"))

    return render_template("shop/register.html")





@shop_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        pincode = request.form.get("pincode")
        email = request.form.get("email")

        shop = Shopkeeper.query.filter(
            func.lower(Shopkeeper.shop_name)==shop_name.lower(),
            Shopkeeper.pincode==pincode,
            func.lower(Shopkeeper.email)==email.lower()
        ).first()

        if not shop:
            flash("Invalid credentials", "danger")
            return redirect(url_for("shop.login"))

        start_otp_flow("shop_login", email, shop.shopkeeper_name, {"shop_id":shop.id})
        return redirect(url_for("shop.verify_otp_view"))

    return render_template("shop/login.html")

@shop_bp.route("/verify-otp", methods=["GET","POST"])
def verify_otp_view():
    rec = get_current_record()
    if not rec:
        return redirect(url_for("shop.login"))

    if request.method=="POST":
        ok,data = verify_otp(request.form.get("otp"), "shop_login")
        if not ok:
            flash(data,"danger")
            return redirect(url_for("shop.verify_otp_view"))
        session["shop_id"] = data["payload"]["shop_id"]
        return redirect(url_for("shop.dashboard"))

    return render_template("auth/verify_otp.html", email=rec.email, role="shop")






@shop_bp.route("/dashboard")
def dashboard():
    shop = _get_logged_in_shop()
    if not shop:
        return redirect(url_for("shop.login"))

    today = date.today()
    products = Product.query.filter_by(shopkeeper_id=shop.id).all()

    total_stock_value = 0
    low_stock_items = 0
    expired, expiring_soon = [], []
    low_stock_threshold_default = 10
    stock_labels, stock_values = [], []

    for p in products:
        qty = p.quantity or 0
        price = float(p.price or 0)
        total_stock_value += qty * price

        threshold = p.low_stock_threshold or low_stock_threshold_default
        if qty <= threshold:
            low_stock_items += 1

        if p.expiry_date:
            if p.expiry_date < today:
                expired.append(p)
            elif (p.expiry_date - today).days <= 7:
                expiring_soon.append(p)

        if qty>0:
            stock_labels.append(p.product_name)
            stock_values.append(round(qty*price,2))

    sales = Sale.query.filter_by(shopkeeper_id=shop.id).all()
    today_sales_total, today_profit, today_units = 0,0,0
    monthly_profit = 0

    for s in sales:
        cp = s.product.cost_price if s.product and s.product.cost_price else s.unit_price
        profit = (float(s.unit_price) - float(cp)) * int(s.quantity)

        if s.created_at.date()==today:
            today_sales_total+=s.total_price
            today_profit+=profit
            today_units+=s.quantity
        if s.created_at.month==today.month:
            monthly_profit+=profit
        
    last7_start = today - timedelta(days=6)
    daily_map = {}

    for s in sales:
        d = s.created_at.date()
        if d < last7_start or d > today:
            continue

        qty = s.quantity or 0
        unit_price = float(s.unit_price or 0)
        total_price = float(s.total_price or 0)

        if s.product and s.product.cost_price is not None:
           cp = float(s.product.cost_price)
        else:
            cp = float(unit_price)

        profit = (float(unit_price) - cp) * qty

        if d not in daily_map:
            daily_map[d] = {"sales": 0.0, "profit": 0.0}

        daily_map[d]["sales"] += total_price
        daily_map[d]["profit"] += profit

    sales_labels = []
    sales_amounts = []
    sales_profits = []

    for i in range(7):
        day = last7_start + timedelta(days=i)
        info = daily_map.get(day, {"sales": 0.0, "profit": 0.0})
        sales_labels.append(day.strftime("%d %b"))
        sales_amounts.append(round(info["sales"], 2))
        sales_profits.append(round(info["profit"], 2))
    stats={
        "todays_sales":round(today_sales_total,2),
        "todays_profit":round(today_profit,2),
        "monthly_profit":round(monthly_profit,2),
        "monthly_loss":0 if monthly_profit>0 else abs(monthly_profit),
        "total_units_sold_today":today_units,
        "total_stock_value":round(total_stock_value,2),
        "low_stock_items":low_stock_items
    }

   
    if low_stock_items or expired or expiring_soon:
        low_lines=[]
        for p in products:
            qty=p.quantity or 0
            threshold=p.low_stock_threshold or low_stock_threshold_default
            if qty<=threshold:
                low_lines.append(f"{p.product_name}: {qty} left")

        all_lines=[]
        if low_lines:
            all_lines+=["Low stock:"]+low_lines+[""]
        if expired:
            all_lines+=["Expired items:"]+[p.product_name for p in expired]+[""]
        if expiring_soon:
            all_lines+=["Expiring soon:"]+[p.product_name for p in expiring_soon]

        _send_inventory_alert_email(shop,"Inventory Alert",all_lines)
 


    if 'sales_labels' not in locals():
        sales_labels = []
        sales_amounts = []
        sales_profits = []

    if 'stock_labels' not in locals():
        stock_labels = []
        stock_values = []

    
    from sqlalchemy import func

    online_revenue = (
       db.session.query(func.coalesce(func.sum(OnlineTransaction.amount), 0))
       .filter(OnlineTransaction.shop_id == shop.id)
       .scalar()
    )

    online_revenue = round(float(online_revenue or 0), 2)


   
    orders = Order.query.filter_by(shop_id=shop.id).order_by(Order.created_at.desc()).limit(15).all()

    return render_template(
        "shop/dashboard.html",
        shop=shop,
        stats=stats,
        products=products,
        sales_labels=sales_labels,
        sales_amounts=sales_amounts,
        sales_profits=sales_profits,
        stock_labels=stock_labels,
        stock_values=stock_values,
        online_revenue=online_revenue,
        orders=orders,
        active_page="dashboard",
    )

@shop_bp.route("/api/order/update_status", methods=["POST"])
def update_order_status():
    shop = _get_logged_in_shop()
    if not shop:
        return jsonify({"success": False, "message": "Not authenticated"})
    data = request.get_json() or {}
    oid = data.get("order_id")
    status = data.get("status")
    order = Order.query.filter_by(id=oid, shop_id=shop.id).first()
    if not order:
        return jsonify({"success": False, "message": "Order not found"})
    order.status = status
    db.session.commit()
    if order.user and order.user.email:
        try:
            subj = f"Update on your Dundoo Order #{order.id}"
            body = f"Hello {order.user.username},\n\nYour order for {order.product.product_name} is now: {status}.\n\nThank you for shopping nearby with Dundoo!"
            send_inventory_email(order.user.email, subj, body)
        except Exception:
            pass
    return jsonify({"success": True, "status": status})

from sqlalchemy import func

@shop_bp.route("/online-transactions")
def online_transactions():
    shop = _get_logged_in_shop()
    if not shop:
        return redirect(url_for("shop.login"))

    selected_date = request.args.get("date")

    q = OnlineTransaction.query.filter_by(shop_id=shop.id)

    if selected_date:
        q = q.filter(func.date(OnlineTransaction.created_at) == selected_date)

    txns = q.order_by(OnlineTransaction.created_at.desc()).all()

    return render_template(
        "shop/online_txns.html",
        txns=txns,
        selected_date=selected_date,
        active_page="online_txns"
    )



@shop_bp.route("/logout")
def logout():
    session.pop("shop_id", None)
    flash("Shopkeeper logged out.", "info")
    return redirect(url_for("shop.login"))



@shop_bp.route("/add-product", methods=["GET", "POST"])
def add_product():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    if request.method == "POST":
        name = (request.form.get("product_name") or "").strip()
        desc = (request.form.get("description") or "").strip()
        price = request.form.get("price", type=float)
        cost_price = request.form.get("cost_price", type=float)
        qty = request.form.get("quantity", type=int) or 0
        available = request.form.get("available") == "on"
        category = (request.form.get("category") or "").strip() or None

        low_threshold = request.form.get("low_stock_threshold", type=int) or 10
        expiry_raw = request.form.get("expiry_date")
        expiry_date = None
        if expiry_raw:
            try:
                expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d").date()
            except ValueError:
                expiry_date = None

        if not name:
            flash("Product name is required.", "danger")
            return redirect(url_for("shop.add_product"))

        p = Product(
            shopkeeper_id=shop.id,
            product_name=name,
            description=desc or None,
            price=price,
            cost_price=cost_price,
            quantity=qty,
            opening_stock=qty,
            added_stock=0,
            damaged_stock=0,
            low_stock_threshold=low_threshold,
            expiry_date=expiry_date,
            available=available,
            category=category,
        )

        
        
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
            if ext not in allowed:
                flash("Invalid image type. Allowed: png, jpg, jpeg, gif.", "danger")
                return redirect(url_for("shop.add_product"))

            p.image_filename = upload_image(image_file, folder="dundoo/products", prefix=str(shop.id))
        else:
            p.image_filename = p.display_image

        db.session.add(p)
        db.session.commit()

        
        if qty > 0:
            sm = StockMovement(
                shop_id=shop.id,
                product_id=p.id,
                change_type="IN",
                quantity=qty,
                unit_cost=cost_price or price,
                note="Initial stock",
            )
            db.session.add(sm)
            db.session.commit()

        flash("Product added.", "success")
        return redirect(url_for("shop.stock"))

    return render_template(
        "shop/add_product.html", shop=shop, is_edit=False, active_page="stock"
    )



@shop_bp.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    product = Product.query.filter_by(
        id=product_id, shopkeeper_id=shop.id
    ).first_or_404()

    if request.method == "POST":
        product.product_name = (request.form.get("product_name") or "").strip()
        product.description = (request.form.get("description") or "").strip() or None
        product.category = (request.form.get("category") or "").strip() or None
        product.price = request.form.get("price", type=float)
        product.cost_price = request.form.get("cost_price", type=float)
        product.quantity = request.form.get("quantity", type=int) or 0
        product.low_stock_threshold = (
            request.form.get("low_stock_threshold", type=int) or 10
        )

        expiry_raw = request.form.get("expiry_date")
        if expiry_raw:
            try:
                product.expiry_date = datetime.strptime(
                    expiry_raw, "%Y-%m-%d"
                ).date()
            except ValueError:
                product.expiry_date = None
        else:
            product.expiry_date = None

       
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            allowed = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
            if ext in allowed:
                product.image_filename = upload_image(image_file, folder="dundoo/products", prefix=str(shop.id))
        if not product.image_filename:
            product.image_filename = product.display_image

        db.session.commit()
        flash("Product updated successfully.", "success")
        return redirect(url_for("shop.stock"))

    return render_template(
        "shop/edit_product.html",
        shop=shop,
        product=product,
        is_edit=True,
        active_page="stock",
    )



@shop_bp.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    product = Product.query.get_or_404(product_id)
    if product.shopkeeper_id != shop.id:
        flash("You cannot delete this product.", "danger")
        return redirect(url_for("shop.stock"))

    sales_count = Sale.query.filter_by(product_id=product.id).count()
    if sales_count > 0:
        product.available = False
        db.session.commit()
        flash(
            "This product has sales history, so it cannot be deleted. "
            "We have marked it as unavailable instead.",
            "warning",
        )
        return redirect(url_for("shop.stock"))

    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("shop.stock"))



@shop_bp.route("/toggle-product/<int:product_id>", methods=["POST"])
def toggle_product(product_id):
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    product = Product.query.get_or_404(product_id)
    if product.shopkeeper_id != shop.id:
        flash("You cannot modify this product.", "danger")
        return redirect(url_for("shop.dashboard"))

    product.available = not product.available
    db.session.commit()
    flash("Product availability updated.", "success")
    return redirect(url_for("shop.dashboard"))


@shop_bp.route("/api/product/quick_toggle", methods=["POST"])
def quick_toggle_api():
    shop = _get_logged_in_shop()
    if not shop:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    data = request.get_json() or {}
    pid = data.get("product_id")
    try:
        product = Product.query.get(int(pid))
    except (ValueError, TypeError):
        product = None
    if not product or product.shopkeeper_id != shop.id:
        return jsonify({"success": False, "message": "Product not found"}), 404
    if "available" in data:
        product.available = bool(data["available"])
    if "price" in data:
        try:
            product.price = float(data["price"])
        except (ValueError, TypeError):
            pass
    if "quantity" in data:
        try:
            product.quantity = int(data["quantity"])
        except (ValueError, TypeError):
            pass
    db.session.commit()
    return jsonify({"success": True, "available": product.available, "price": product.price, "quantity": product.quantity})



@shop_bp.route("/products")
def products():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    search = (request.args.get("search") or "").strip()
    category = (request.args.get("category") or "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    base_query = Product.query.filter_by(shopkeeper_id=shop.id)

    if search:
        ilike = f"%{search}%"
        base_query = base_query.filter(Product.product_name.ilike(ilike))

    if category:
        base_query = base_query.filter(
            func.lower(Product.category) == category.lower()
        )

    pagination = base_query.order_by(Product.product_name.asc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    products_list = pagination.items

    categories_rows = (
        db.session.query(Product.category)
        .filter_by(shopkeeper_id=shop.id)
        .filter(Product.category.isnot(None))
        .distinct()
        .all()
    )
    categories = sorted([c[0] for c in categories_rows if c[0]])

    all_products_for_alerts = Product.query.filter_by(shopkeeper_id=shop.id).all()
    low_stock = [
        p
        for p in all_products_for_alerts
        if (p.quantity or 0) <= (p.low_stock_threshold or 10)
    ]

    chart_labels = [p.product_name for p in products_list]
    chart_values = [int(p.quantity or 0) for p in products_list]

    return render_template(
        "shop/manage_products.html",
        shop=shop,
        products=products_list,
        pagination=pagination,
        search=search,
        category=category,
        categories=categories,
        low_stock=low_stock,
        chart_labels=chart_labels,
        chart_values=chart_values,
        active_page="stock",
    )




@shop_bp.route("/add-stock/<int:product_id>", methods=["GET", "POST"])
def add_stock(product_id):
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login first.", "danger")
        return redirect(url_for("shop.login"))

    product = Product.query.get_or_404(product_id)
    if product.shopkeeper_id != shop.id:
        flash("You cannot modify this product.", "danger")
        return redirect(url_for("shop.products"))

    if request.method == "POST":
        amount = request.form.get("amount", type=int) or 0
        if amount <= 0:
            flash("Enter a positive quantity to add.", "danger")
            return redirect(url_for("shop.add_stock", product_id=product.id))

        product.quantity += amount
        product.added_stock += amount
        db.session.commit()

        sm = StockMovement(
            shop_id=shop.id,
            product_id=product.id,
            change_type="IN",
            quantity=amount,
            unit_cost=product.cost_price or product.price,
            note="Added stock",
        )
        db.session.add(sm)
        db.session.commit()

        flash(f"Added {amount} units to {product.product_name}.", "success")
        return redirect(url_for("shop.products"))

    return render_template(
        "shop/add_stock.html", product=product, shop=shop, active_page="stock"
    )




@shop_bp.route("/stock", methods=["GET", "POST"])
def stock():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    if request.method == "POST":
        action = request.form.get("action")
        product_id = request.form.get("product_id", type=int)
        amount = request.form.get("amount", type=int) or 0

        product = Product.query.filter_by(
            id=product_id, shopkeeper_id=shop.id
        ).first_or_404()

        if action == "add":
            if amount > 0:
                product.quantity += amount
                product.added_stock += amount
                flash(f"Added {amount} units to {product.product_name}.", "success")
        elif action == "damage":
            if amount > 0:
                if amount > product.quantity:
                    flash("Cannot mark more damaged than current stock.", "danger")
                else:
                    product.quantity -= amount
                    product.damaged_stock += amount
                    flash(
                        f"Marked {amount} units of {product.product_name} as damaged.",
                        "warning",
                    )

        db.session.commit()
        return redirect(url_for("shop.stock"))

    
    products = Product.query.filter_by(shopkeeper_id=shop.id).all()

    today = date.today()
    low_stock = []
    expired = []
    expiring_soon = []

    for p in products:
        threshold = p.low_stock_threshold or 10
        if (p.quantity or 0) <= threshold:
            low_stock.append(p)

        if p.expiry_date:
            if p.expiry_date < today:
                expired.append(p)
            elif (p.expiry_date - today).days <= 7:
                expiring_soon.append(p)

    
    email_lines = []

    if low_stock:
        email_lines.append("Low stock items:")
        for p in low_stock:
            threshold = p.low_stock_threshold or 10
            email_lines.append(
                f"- {p.product_name}: {p.quantity} left (threshold {threshold})"
            )
        email_lines.append("")

    if expired:
        email_lines.append("Expired items:")
        for p in expired:
            email_lines.append(f"- {p.product_name}: expired on {p.expiry_date}")
        email_lines.append("")

    if expiring_soon:
        email_lines.append("Expiring within 7 days:")
        for p in expiring_soon:
            email_lines.append(f"- {p.product_name}: expires on {p.expiry_date}")

    if email_lines:
        _send_inventory_alert_email(
            shop,
            subject="Inventory alert: low/expiring stock",
            lines=email_lines,
        )

    return render_template(
        "shop/stock.html",
        shop=shop,
        products=products,
        low_stock=low_stock,
        expired=expired,
        expiring_soon=expiring_soon,
        today=date.today(),            
        active_page="stock",
    )


@shop_bp.route("/record-sale", methods=["GET", "POST"])
def record_sale():
    shop = _get_logged_in_shop()
    if not shop:
        return redirect(url_for("shop.login"))

    products = Product.query.filter_by(shopkeeper_id=shop.id).all()

    if request.method == "POST":
        product_id = request.form.get("product_id", type=int)
        qty = request.form.get("quantity", type=int)
        customer_name = request.form.get("customer_name","").strip()
        customer_mobile = request.form.get("customer_mobile","").strip()
        payment_mode = request.form.get("payment_mode")

        product = Product.query.filter_by(id=product_id, shopkeeper_id=shop.id).first_or_404()

        if qty <= 0 or qty > product.quantity:
            flash("Invalid quantity", "danger")
            return redirect(url_for("shop.record_sale"))

        total_price = float(product.price) * qty

        
        if payment_mode == "offline":
            product.quantity -= qty

            sale = Sale(
                shopkeeper_id=shop.id,
                product_id=product.id,
                quantity=qty,
                unit_price=product.price,
                total_price=total_price,
                customer_name=customer_name or None,
            )
            db.session.add(sale)

            sm = StockMovement(
                shop_id=shop.id,
                product_id=product.id,
                change_type="OUT",
                quantity=qty,
                unit_cost=product.cost_price or product.price,
                note="Offline Sale"
            )
            db.session.add(sm)
            db.session.commit()

            if customer_mobile.isdigit() and len(customer_mobile)==10:
                import urllib.parse
                msg = f"Thank you for shopping at {shop.shop_name}. Bill ₹{total_price:.2f}"
                session["whatsapp_link"] = f"https://wa.me/91{customer_mobile}?text={urllib.parse.quote(msg)}"

            flash("✅ Offline sale recorded", "success")
            return redirect(url_for("shop.record_sale"))

        
        session["pending_sale"] = {
            "product_id": product.id,
            "qty": qty,
            "total_price": total_price,
            "customer_name": customer_name,
            "customer_mobile": customer_mobile
        }

        flash("Proceed with online payment", "info")
        return redirect(url_for("shop.record_sale"))

    return render_template("shop/record_sale.html",
        shop=shop,
        products=products,
        pending_sale=session.get("pending_sale"),
        razorpay_key=current_app.config["RAZORPAY_KEY_ID"],
        active_page="record_sale"
    )

@shop_bp.route("/record-sale/<int:product_id>", methods=["GET", "POST"])
def record_sale_product(product_id):
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login first.", "danger")
        return redirect(url_for("shop.login"))

    product = Product.query.get_or_404(product_id)
    if product.shopkeeper_id != shop.id:
        flash("You cannot sell this product.", "danger")
        return redirect(url_for("shop.products"))

    if request.method == "POST":
        qty = request.form.get("quantity", type=int) or 0
        customer_name = (request.form.get("customer_name") or "").strip()

        if qty <= 0:
            flash("Quantity must be greater than 0.", "danger")
            return redirect(
                url_for("shop.record_sale_product", product_id=product.id)
            )

        if qty > (product.quantity or 0):
            flash("Not enough stock available.", "danger")
            return redirect(
                url_for("shop.record_sale_product", product_id=product.id)
            )

        unit_price = float(product.price or 0)
        total_price = unit_price * qty

        sale = Sale(
            shopkeeper_id=shop.id,
            product_id=product.id,
            quantity=qty,
            unit_price=unit_price,
            total_price=total_price,
            customer_name=customer_name or None,
        )
        product.quantity -= qty

        db.session.add(sale)
        db.session.commit()

        sm = StockMovement(
            shop_id=shop.id,
            product_id=product.id,
            change_type="OUT",
            quantity=qty,
            unit_cost=product.cost_price or product.price,
            note=f"Sale to {customer_name or 'customer'} (single-product form)",
        )
        db.session.add(sm)
        db.session.commit()

        flash(
            f"Sale recorded: {qty} × {product.product_name} (₹{total_price:.2f}).",
            "success",
        )
        return redirect(url_for("shop.products"))

    return render_template(
        "shop/record_sale_single.html",
        product=product,
        shop=shop,
        active_page="record_sale",
    )



@shop_bp.route("/products/bulk-upload", methods=["GET", "POST"])
def bulk_upload_products():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please choose an Excel file.", "danger")
            return redirect(url_for("shop.bulk_upload_products"))

        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("xlsx", "xls"):
            flash("Only Excel files (.xlsx, .xls) are allowed.", "danger")
            return redirect(url_for("shop.bulk_upload_products"))

        try:
            import openpyxl
        except ImportError:
            flash("openpyxl not installed. Run: pip install openpyxl", "danger")
            return redirect(url_for("shop.bulk_upload_products"))

        wb = openpyxl.load_workbook(file)
        ws = wb.active

        created_count = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            name, description, price, quantity, category = (row + (None,) * 5)[:5]

            if not name:
                continue

            q = int(quantity) if quantity is not None else 0
            p = Product(
                shopkeeper_id=shop.id,
                product_name=str(name).strip(),
                description=str(description).strip() if description else None,
                price=float(price) if price is not None else None,
                quantity=q,
                opening_stock=q,
                added_stock=0,
                damaged_stock=0,
                category=str(category).strip() if category else None,
            )
            db.session.add(p)
            created_count += 1

        db.session.commit()
        flash(f"Imported {created_count} products from Excel.", "success")
        return redirect(url_for("shop.products"))

    return render_template(
        "shop/bulk_upload.html", shop=shop, active_page="stock"
    )





def _get_period_dates(period: str):
    """Return (start_date, end_date) for 'today' / 'month' / '6months'."""
    today = date.today()

    if period == "today":
        start = today
        end = today
    elif period == "6months":
        
        month = today.month - 5
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        start = date(year, month, 1)
        end = today
    else:  
        start = today.replace(day=1)
        end = today

    return start, end


def _load_sales_for_period(shop, start_date: date, end_date: date):
    """All sales for a shop between start_date and end_date (inclusive)."""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    return (
        Sale.query.filter_by(shopkeeper_id=shop.id)
        .filter(Sale.created_at >= start_dt, Sale.created_at < end_dt)
        .order_by(Sale.created_at.desc())
        .all()
    )


def _build_sales_summary(sales):
    total_sales = 0.0
    total_profit = 0.0
    total_qty = 0
    product_map = {}
    category_map = {}

    for s in sales:
        qty = s.quantity or 0
        amount = float(s.total_price or 0)
        total_sales += amount
        total_qty += qty

        sp = float(s.unit_price or 0)
        cp = float(s.product.cost_price) if s.product and s.product.cost_price else sp
        profit = (sp - cp) * qty
        total_profit += profit

        pname = s.product.product_name if s.product else "Unknown"
        cat = s.product.category if s.product and s.product.category else "Uncategorized"

        if s.product_id not in product_map:
            product_map[s.product_id] = {
                "product_name": pname,
                "category": cat,
                "quantity": 0,
                "amount": 0.0,
                "profit": 0.0,
            }

        product_map[s.product_id]["quantity"] += qty
        product_map[s.product_id]["amount"] += amount
        product_map[s.product_id]["profit"] += profit

        if cat not in category_map:
            category_map[cat] = {"amount": 0.0, "profit": 0.0}

        category_map[cat]["amount"] += amount
        category_map[cat]["profit"] += profit

    return {
        "total_sales": round(total_sales, 2),
        "total_profit": round(total_profit, 2),
        "total_qty": total_qty,
        "products": list(product_map.values()),
        "categories": [
            {"category": k, "amount": v["amount"], "profit": v["profit"]}
            for k, v in category_map.items()
        ],
    }




@shop_bp.route("/billing")
def billing():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    period = request.args.get("period", "month")  # today / month / 6months
    start_date, end_date = _get_period_dates(period)

    sales = _load_sales_for_period(shop, start_date, end_date)
    summary = _build_sales_summary(sales)

    stats = {
        "paid_today": summary["total_sales"] if period == "today" else 0.0,
        "overdue": 0.0,
        "pending": 0.0,
        "total_invoices": len(sales),
    }

    return render_template(
        "shop/billing.html",
        shop=shop,
        period=period,
        start_date=start_date,
        end_date=end_date,
        stats=stats,
        sales=sales,
        summary=summary,
        active_page="billing",
    )


@shop_bp.route("/billing/pdf")
def billing_pdf():
    """
    Download a PDF summary for a period.
    ?period=today|month|6months  (default month)
    You can also pass explicit ?start=YYYY-MM-DD&end=YYYY-MM-DD
    but we still enforce max 6 months.
    """
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    period = request.args.get("period", "month")
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format for PDF export.", "danger")
            return redirect(url_for("shop.billing", period=period))
    else:
        start_date, end_date = _get_period_dates(period)

    # safety: max 6 months
    if (end_date - start_date).days > 31 * 6:
        flash("You can download at most 6 months of invoice data at once.", "warning")
        return redirect(url_for("shop.billing", period="6months"))

    sales = _load_sales_for_period(shop, start_date, end_date)
    summary = _build_sales_summary(sales)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    title = f"{shop.shop_name} – Invoice Summary"
    period_text = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, title)
    y -= 18
    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Period: {period_text}")
    y -= 24

    # Overall totals
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Totals")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Total quantity sold: {summary['total_qty']}")
    y -= 12
    c.drawString(50, y, f"Total sales: ₹{summary['total_sales']:.2f}")
    y -= 12
    c.drawString(50, y, f"Total profit: ₹{summary['total_profit']:.2f}")
    y -= 20

    # By category
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "By category")
    y -= 14
    c.setFont("Helvetica", 10)
    for row in summary["categories"]:
        line = (
            f"{row['category']}: sales ₹{row['amount']:.2f}, "
            f"profit ₹{row['profit']:.2f}"
        )
        c.drawString(50, y, line)
        y -= 12
        if y < 80:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 10)
    y -= 10

    # By product
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "By product")
    y -= 14
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "Category")
    c.drawString(170, y, "Product")
    c.drawString(330, y, "Qty")
    c.drawString(380, y, "Sales (₹)")
    c.drawString(460, y, "Profit (₹)")
    y -= 12
    c.setFont("Helvetica", 9)

    for row in summary["products"]:
        c.drawString(50, y, row["category"][:18])
        c.drawString(170, y, row["product_name"][:22])
        c.drawRightString(360, y, str(row["quantity"]))
        c.drawRightString(430, y, f"{row['amount']:.2f}")
        c.drawRightString(510, y, f"{row['profit']:.2f}")
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 40
            c.setFont("Helvetica", 9)

    c.showPage()
    c.save()

    buffer.seek(0)
    filename = f"invoices_{start_date.isoformat()}_{end_date.isoformat()}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )



@shop_bp.route("/reports")
def reports():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    today = date.today()

    
    start_30d = today - timedelta(days=29)
    sales_30d = _load_sales_for_period(shop, start_30d, today)
    summary_30d = _build_sales_summary(sales_30d)

    total_sales_30d = summary_30d["total_sales"]
    total_profit_30d = summary_30d["total_profit"]
    total_orders_30d = len(sales_30d)
    avg_order_value = total_sales_30d / total_orders_30d if total_orders_30d else 0.0

    
    prev_start = today - timedelta(days=59)
    prev_end = today - timedelta(days=30)
    sales_prev_30d = _load_sales_for_period(shop, prev_start, prev_end)
    summary_prev_30d = _build_sales_summary(sales_prev_30d)
    prev_sales = summary_prev_30d["total_sales"]
    prev_profit = summary_prev_30d["total_profit"]

    def compute_growth(current, prev):
        
        if prev <= 0 and current <= 0:
            return None
        if prev <= 0:
            return 100.0
        return ((current - prev) / prev) * 100.0

    stats = {
        "total_sales": total_sales_30d,
        "total_profit": total_profit_30d,
        "total_orders": total_orders_30d,
        "avg_order_value": avg_order_value,
        "growth_sales_30d": compute_growth(total_sales_30d, prev_sales),
        "growth_profit_30d": compute_growth(total_profit_30d, prev_profit),
    }

    
    start_6m, end_6m = _get_period_dates("6months")
    sales_6m = _load_sales_for_period(shop, start_6m, end_6m)

    
    month_totals = defaultdict(float)
    for s in sales_6m:
        key = (s.created_at.year, s.created_at.month)
        month_totals[key] += float(s.total_price or 0)

    month_labels = []
    month_values = []

    
    cur_year = today.year
    cur_month = today.month
    months = []
    for i in range(5, -1, -1):  # 5,4,3,2,1,0
        m = cur_month - i
        y = cur_year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    for (y, m) in months:
        label = date(y, m, 1).strftime("%b %Y")
        month_labels.append(label)
        month_values.append(round(month_totals.get((y, m), 0.0), 2))

    return render_template(
        "shop/reports.html",
        shop=shop,
        active_page="reports",
        stats=stats,
        summary_30d=summary_30d,
        month_labels=month_labels,
        month_values=month_values,
    )



@shop_bp.route("/chatbot")
def chatbot():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    return render_template(
        "shop/chatbot.html",
        shop=shop,
        active_page="chatbot",
    )



@shop_bp.route("/settings", methods=["GET", "POST"])
def settings():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    if request.method == "POST":
        
        shop_name = (request.form.get("shop_name") or "").strip()
        shopkeeper_name = (request.form.get("shopkeeper_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        address = (request.form.get("address") or "").strip()
        pincode = (request.form.get("pincode") or "").strip()
        landmark = (request.form.get("landmark") or "").strip()

        if not shop_name or not shopkeeper_name or not email or not address or not pincode:
            flash("All required fields must be filled.", "danger")
            return redirect(url_for("shop.settings"))

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("shop.settings"))

        
        if email.lower() != shop.email.lower():
            other = (
                Shopkeeper.query
                .filter(func.lower(Shopkeeper.email) == email.lower())
                .first()
            )
            if other:
                flash("This email is already used by another account.", "danger")
                return redirect(url_for("shop.settings"))

        
        
        lat_str = (request.form.get("latitude") or "").strip()
        lon_str = (request.form.get("longitude") or "").strip()

        new_lat = shop.latitude
        new_lon = shop.longitude
        if lat_str and lon_str:
            try:
                new_lat = float(lat_str)
                new_lon = float(lon_str)
            except ValueError:
                flash("Could not parse latitude/longitude from browser.", "warning")

        # Save changes
        shop.shop_name = shop_name
        shop.shopkeeper_name = shopkeeper_name
        shop.email = email
        shop.address = address
        shop.pincode = pincode
        shop.landmark = landmark or None
        shop.latitude = new_lat
        shop.longitude = new_lon

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("shop.settings"))

    return render_template(
        "shop/settings.html",
        shop=shop,
        active_page="settings",
    )



@shop_bp.route("/delete-account", methods=["POST"])
def delete_account():
    shop = _get_logged_in_shop()
    if not shop:
        flash("Please login as shopkeeper first.", "warning")
        return redirect(url_for("shop.login"))

    stock_moves = StockMovement.query.filter_by(shop_id=shop.id).all()
    sales = Sale.query.filter_by(shopkeeper_id=shop.id).all()
    expenses = Expense.query.filter_by(shop_id=shop.id).all()
    products = Product.query.filter_by(shopkeeper_id=shop.id).all()

    for sm in stock_moves:
        db.session.delete(sm)

    for s in sales:
        db.session.delete(s)

    for e in expenses:
        db.session.delete(e)

    for p in products:
        db.session.delete(p)

    db.session.delete(shop)
    db.session.commit()

    session.pop("shop_id", None)
    flash("Your shop account and all related data have been deleted.", "info")
    return redirect(url_for("main.home"))






@shop_bp.route("/payment/create-order", methods=["POST"])
def create_order():
    pending = session.get("pending_sale")
    if not pending:
        return {"error": "No pending sale"}, 400

    client = get_razorpay_client()
    amount = int(float(pending["total_price"]) * 100)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    txn = OnlineTransaction(
        shop_id=session["shop_id"],
        razorpay_order_id=order["id"],
        amount=pending["total_price"],
        status="pending"
    )

    db.session.add(txn)
    db.session.commit()

    return {"id": order["id"], "amount": amount}





@shop_bp.route("/payment/success", methods=["POST"])
def payment_success():
    shop = _get_logged_in_shop()
    data = request.get_json()
    pending = session.pop("pending_sale", None)

    if not pending:
        return {"error": "No pending sale"}, 400

    txn = OnlineTransaction.query.filter_by(
        razorpay_order_id=data["razorpay_order_id"]
    ).first_or_404()

    txn.razorpay_payment_id = data["razorpay_payment_id"]
    txn.status = "success"

    product = Product.query.get(pending["product_id"])
    product.quantity -= pending["qty"]

    sale = Sale(
        shopkeeper_id=shop.id,
        product_id=product.id,
        quantity=pending["qty"],
        unit_price=product.price,
        total_price=pending["total_price"],
        customer_name=pending["customer_name"]
    )
    db.session.add(sale)

    sm = StockMovement(
        shop_id=shop.id,
        product_id=product.id,
        change_type="OUT",
        quantity=pending["qty"],
        unit_cost=product.cost_price or product.price,
        note="Online Razorpay Sale"
    )
    db.session.add(sm)

    import urllib.parse
    mobile = pending["customer_mobile"]
    if mobile.isdigit() and len(mobile)==10:
        msg = f"Thank you for shopping at {shop.shop_name}. Bill ₹{pending['total_price']:.2f}"
        session["whatsapp_link"] = f"https://wa.me/91{mobile}?text={urllib.parse.quote(msg)}"

    db.session.commit()

    return {"redirect": url_for("shop.record_sale")}



@shop_bp.route("/reels")
def reels():
    shop = _get_logged_in_shop()
    if not shop:
        return redirect(url_for("shop.login"))

    return render_template(
        "shop/reels.html",
        shop=shop,              
        active_page="reels"
    )





    
