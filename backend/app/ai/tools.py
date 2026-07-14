from app.models import Product
from app import db
from .extractor import extract_number, extract_product_name
from app.shop.routes import _get_logged_in_shop
from datetime import datetime


def add_product_tool(text, session):

    shop = _get_logged_in_shop()

    if not shop:
        return "Please login as shopkeeper first."

    pending = session.get("pending_product", {})

    # 1️⃣ Product Name
    if "name" not in pending:
        name = extract_product_name(text)
        if name:
            pending["name"] = name
            session["pending_product"] = pending
            return f"What is the selling price of {name}?"
        else:
            return "Please tell the product name."

    # 2️⃣ Selling Price
    if "price" not in pending:
        price = extract_number(text)
        if price:
            pending["price"] = price
            session["pending_product"] = pending
            return f"What is the cost price of {pending['name']}?"
        else:
            return "Please tell the selling price in numbers."

    # 3️⃣ Cost Price
    if "cost_price" not in pending:
        cost = extract_number(text)
        if cost:
            pending["cost_price"] = cost
            session["pending_product"] = pending
            return f"What is the quantity of {pending['name']}?"
        else:
            return "Please tell the cost price in numbers."

    # 4️⃣ Quantity
    if "quantity" not in pending:
        qty = extract_number(text)
        if qty:
            pending["quantity"] = int(qty)
            session["pending_product"] = pending
            return f"What category does {pending['name']} belong to?"
        else:
            return "Please tell the quantity in numbers."

    # 5️⃣ Category
    if "category" not in pending:
        pending["category"] = text.strip().title()
        session["pending_product"] = pending
        return f"Does {pending['name']} have an expiry date? (yes or no)"

    # 6️⃣ Expiry Decision
    if "expiry_check" not in pending:
        if "yes" in text.lower():
            pending["expiry_check"] = True
            session["pending_product"] = pending
            return "Enter expiry date in YYYY-MM-DD format."
        else:
            pending["expiry_check"] = False
            pending["expiry_date"] = None
            session["pending_product"] = pending

            return finalize_product(pending, shop, session)

    # 7️⃣ Expiry Date
    if pending.get("expiry_check") and "expiry_date" not in pending:
        try:
            expiry = datetime.strptime(text.strip(), "%Y-%m-%d").date()
            pending["expiry_date"] = expiry
            session["pending_product"] = pending
            return finalize_product(pending, shop, session)
        except:
            return "Please enter expiry date in YYYY-MM-DD format."

    return "Processing..."


def finalize_product(pending, shop, session):

    product = Product(
        shopkeeper_id=shop.id,
        product_name=pending["name"],
        description="",
        category=pending["category"],
        price=pending["price"],
        quantity=pending["quantity"],
        opening_stock=pending["quantity"],
        added_stock=pending["quantity"],
        damaged_stock=0,
        low_stock_threshold=10,
        cost_price=pending["cost_price"],
        expiry_date=pending.get("expiry_date"),
        available=True
    )

    db.session.add(product)
    db.session.commit()

    session.pop("pending_product")

    return f"{pending['name']} product added successfully."