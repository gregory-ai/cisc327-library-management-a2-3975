import os
import pytest
from flask import Flask
from database import get_db_connection
from routes.catalog_routes import catalog_bp
from routes.borrowing_routes import borrowing_bp
from routes.search_routes import search_bp
from routes.reports_routes import reports_bp

def reset_database():
    """
    Reset the database by clearing all tables.
    """
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM borrow_records")
        conn.execute("DELETE FROM books")
        conn.commit()
    finally:
        conn.close()

@pytest.fixture(autouse=True)
def clear_db():
    reset_database()
    yield

@pytest.fixture
def app():
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = "test_secret_key"
    app.config["TESTING"] = True

    # Register all blueprints
    app.register_blueprint(catalog_bp)
    app.register_blueprint(borrowing_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(reports_bp)

    yield app

@pytest.fixture
def client(app):
    return app.test_client()