from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("dundoo/index.html")

@main_bp.route("/dundoo-dashboard")
def dundoo_dashboard():
    return render_template("dundoo/dashboard.html")

