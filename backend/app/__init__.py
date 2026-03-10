import logging
from flask import Flask
from flask_cors import CORS
from app.models.database import init_db
from app.routes.routes import api
from app.workers.notification_worker import start_worker_thread


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)


def create_app() -> Flask:
    app = Flask(__name__)

    # Enable CORS for frontend
    CORS(
        app,
        resources={r"/api/*": {"origins": [
            "http://localhost:3000",
            "http://localhost:5173"
        ]}}
    )

    # Register routes
    app.register_blueprint(api)

    # Bootstrap DB schema + seed slots
    with app.app_context():
        init_db()

    # Start background notification worker (daemon thread)
    start_worker_thread()

    return app