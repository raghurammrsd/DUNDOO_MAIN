from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy import text
from .config import Config
from dotenv import load_dotenv
import os

load_dotenv()

try:
    from flask_cors import CORS
except ImportError:
    CORS = None

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "user.login"


_worker_pid = None


def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.getenv("FLASK_TEMPLATE_FOLDER", os.path.join(base_dir, "../../frontend/templates"))
    static_dir = os.getenv("FLASK_STATIC_FOLDER", os.path.join(base_dir, "../../frontend/static"))

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )

    if CORS is not None:
        CORS(app, supports_credentials=True)

    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)

    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE shopkeepers ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
            db.session.execute(text("ALTER TABLE shopkeepers ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(20);"))
            db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(20);"))
            db.create_all()
            db.session.commit()
        except Exception as e:
            db.session.rollback()

    @app.before_request
    def ensure_db_connection():
        global _worker_pid
        current_pid = os.getpid()
        if _worker_pid != current_pid:
            _worker_pid = current_pid
            db.session.remove()
            if hasattr(db, "engine"):
                db.engine.dispose()

        if request.path.startswith("/static/") or request.path == "/favicon.ico":
            return
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            app.logger.warning(f"Connection dropped or stale ({e}). Resetting session & engine...")
            db.session.rollback()
            db.session.remove()
            if hasattr(db, "engine"):
                db.engine.dispose()
            try:
                db.session.execute(text("SELECT 1"))
            except Exception as e2:
                app.logger.error(f"Database pre-request recovery failed: {e2}")

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            db.session.rollback()
        db.session.remove()

    with app.app_context():
        from app.models import User, Shopkeeper, Product, Order, Wishlist, FavoriteShop, Review
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database sync check skipped or errored ({e})")
        finally:
            if hasattr(db, "engine"):
                db.engine.dispose()

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error loading user {user_id}: {e}")
            return None

    
    from app.main.routes import main_bp
    from app.user.routes import user_bp
    from app.shop.routes import shop_bp
    from app.ai.routes import ai_bp
    from app.reels.routes import reels_bp

    app.register_blueprint(reels_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(shop_bp, url_prefix="/shop")
    app.register_blueprint(ai_bp)

    
    app.config["RAZORPAY_KEY_ID"] = os.getenv("RAZORPAY_KEY_ID", "rzp_test_1234567890dummy")
    app.config["RAZORPAY_KEY_SECRET"] = os.getenv("RAZORPAY_KEY_SECRET", "dummy_secret_1234567890")

    return app
