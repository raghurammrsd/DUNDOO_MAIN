from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import Product, Sale
from app.shop.routes import _get_logged_in_shop


def analyze_business():

    shop = _get_logged_in_shop()
    if not shop:
        return "Please login as shopkeeper first."

    insights = []

    # ----------------------------
    # 1️⃣ Revenue Last 7 Days
    # ----------------------------
    last_week = datetime.utcnow() - timedelta(days=7)

    revenue = db.session.query(
        func.sum(Sale.total_price)
    ).filter(
        Sale.shopkeeper_id == shop.id,
        Sale.created_at >= last_week
    ).scalar() or 0

    insights.append(f"Last 7 days revenue: ₹{round(revenue,2)}")

    # ----------------------------
    # 2️⃣ Low Stock Items
    # ----------------------------
    low_stock = Product.query.filter(
        Product.shopkeeper_id == shop.id,
        Product.quantity <= Product.low_stock_threshold
    ).all()

    if low_stock:
        names = ", ".join([p.product_name for p in low_stock])
        insights.append(f"Low stock items: {names}")
    else:
        insights.append("No low stock items.")

    # ----------------------------
    # 3️⃣ Low Profit Products
    # ----------------------------
    products = Product.query.filter_by(
        shopkeeper_id=shop.id
    ).all()

    low_profit = []

    for p in products:
        if p.cost_price and p.price:
            margin = float(p.price) - float(p.cost_price)
            if margin < 5:   # low margin threshold
                low_profit.append(p.product_name)

    if low_profit:
        insights.append(
            "Low profit products: " + ", ".join(low_profit)
        )

    # ----------------------------
    # 4️⃣ Top Selling Products
    # ----------------------------
    top_products = db.session.query(
        Product.product_name,
        func.sum(Sale.quantity).label("total_sold")
    ).join(Sale).filter(
        Sale.shopkeeper_id == shop.id
    ).group_by(Product.product_name
    ).order_by(
        func.sum(Sale.quantity).desc()
    ).limit(3).all()

    if top_products:
        names = ", ".join([p[0] for p in top_products])
        insights.append(f"Top selling products: {names}")

    return "\n".join(insights)