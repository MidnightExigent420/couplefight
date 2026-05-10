import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from flask_login import current_user

from .extensions import db, migrate, login_manager, csrf, limiter

load_dotenv()


def create_app():
    app = Flask(__name__, instance_relative_config=False)

    secret = os.environ.get("SECRET_KEY")
    if not secret:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError("SECRET_KEY must be set in production")
        secret = "dev-only-insecure-key-change-me"

    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///couplefight.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        WTF_CSRF_TIME_LIMIT=None,
        FX_API_BASE=os.environ.get("FX_API_BASE", "https://api.frankfurter.app"),
        SUPPORTED_CURRENCIES=["USD", "EUR", "GBP", "SGD", "JPY", "AUD", "CAD", "CHF", "CNY", "HKD", "INR", "NZD"],
    )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from .auth.routes import bp as auth_bp
    from .dashboard.routes import bp as dashboard_bp
    from .spend.routes import bp as spend_bp
    from .goals.routes import bp as goals_bp
    from .tripwires.routes import bp as tripwires_bp
    from .notifications.routes import bp as notifications_bp
    from .categories.routes import bp as categories_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(spend_bp, url_prefix="/spend")
    app.register_blueprint(goals_bp, url_prefix="/goals")
    app.register_blueprint(tripwires_bp, url_prefix="/tripwires")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(categories_bp, url_prefix="/categories")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.home"))
        return redirect(url_for("auth.login"))

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://cdn.tailwindcss.com 'unsafe-inline'; "
            "style-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    return app
