from datetime import datetime
from flask_login import UserMixin
from app import db



class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    phone = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    



class Shopkeeper(db.Model):
    __tablename__ = "shopkeepers"

    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False)
    shopkeeper_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_hash = db.Column(db.String(255), nullable=True)
    whatsapp_number = db.Column(db.String(20), nullable=True)

    



class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    shopkeeper_id = db.Column(
        db.Integer,
        db.ForeignKey("shopkeepers.id"),
        nullable=False,
    )

    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    
    
    category = db.Column(db.String(50))

    price = db.Column(db.Numeric(10, 2))
    quantity = db.Column(db.Integer, default=0)

    
    opening_stock = db.Column(db.Integer, default=0)
    added_stock = db.Column(db.Integer, default=0)
    damaged_stock = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    expiry_date = db.Column(db.Date, nullable=True)

    
    cost_price = db.Column(db.Numeric(10, 2))

    available = db.Column(db.Boolean, default=True)
    image_filename = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shop = db.relationship("Shopkeeper", backref="products")

    @property
    def display_image(self):
        if self.image_filename and str(self.image_filename).strip() and str(self.image_filename) != "None":
            return self.image_filename
        name = (self.product_name or "").lower()
        if "apple" in name:
            return "1_1764921114_download_apple.jpeg"
        if "banana" in name or "kiwi" in name or "fruit" in name:
            return "1_1764921155_download.jpeg"
        if "straw" in name or "berry" in name:
            return "1_1764921217_download_1strwa.jpeg"
        if "chicken" in name or "meat" in name or "egg" in name:
            return "2_1764922041_chicken.jpeg"
        if "mutton" in name or "fish" in name:
            return "2_1764922116_mutton.jpeg"
        if "piz" in name or "cheese" in name:
            return "2_1764922183_piz.jpeg"
        if "burger" in name or "snack" in name or "bread" in name:
            return "2_1764923003_burger.jpeg"
        if "sugar" in name or "salt" in name or "rice" in name or "atta" in name or "flour" in name or "dal" in name or "oil" in name or "milk" in name or "curd" in name:
            return "1_1783415548_sugar-shutterstock_615908132.jpg"
        return "1_1783415630_images_1.jpeg"

    @property
    def image_url(self):
        img = self.display_image
        if not img:
            return "/static/uploads/products/1_1783415630_images_1.jpeg"
        if img.startswith("http://") or img.startswith("https://") or img.startswith("/"):
            return img
        return f"/static/uploads/products/{img}"






class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)

    shopkeeper_id = db.Column(
        db.Integer,
        db.ForeignKey("shopkeepers.id"),
        nullable=False,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
    )

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    customer_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", backref="sales")
    shopkeeper = db.relationship("Shopkeeper", backref="sales")





class OTPRequest(db.Model):
    __tablename__ = "otp_requests"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    context = db.Column(db.String(50), nullable=False)
    payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    change_type = db.Column(db.String(10))  
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2)) 
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")
    shop = db.relationship("Shopkeeper", backref="stock_moves")



class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shop = db.relationship("Shopkeeper", backref="expenses")
    
class OnlineTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer)
    razorpay_order_id = db.Column(db.String(120))
    razorpay_payment_id = db.Column(db.String(120))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LoyaltyPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(15), unique=True)
    points = db.Column(db.Integer, default=0)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=False)

    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float)

    status = db.Column(db.String(30), default="Placed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="orders")
    product = db.relationship("Product")
    shopkeeper = db.relationship("Shopkeeper")


class Wishlist(db.Model):
    __tablename__ = "wishlist"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


class FavoriteShop(db.Model):
    __tablename__ = "favorite_shops"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shopkeeper = db.relationship("Shopkeeper")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=True)
    rating = db.Column(db.Integer, nullable=False, default=5)
    comment = db.Column(db.Text)
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    product = db.relationship("Product")
    shopkeeper = db.relationship("Shopkeeper")

    @property
    def image_url(self):
        if not self.image:
            return None
        if self.image.startswith("http://") or self.image.startswith("https://") or self.image.startswith("/"):
            return self.image
        return f"/static/uploads/reviews/{self.image}"


class WhatsAppMessage(db.Model):
    __tablename__ = "whatsapp_messages"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shopkeepers.id"), nullable=True)
    recipient_number = db.Column(db.String(30), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message_body = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default="alert")
    status = db.Column(db.String(50), default="SENT")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shop = db.relationship("Shopkeeper", backref=db.backref("whatsapp_messages", lazy=True))

