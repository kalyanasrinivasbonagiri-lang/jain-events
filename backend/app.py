import os

from flask import Flask, jsonify, send_from_directory
from pymongo.errors import PyMongoError

from backend.database import init_database, mongo
from backend.routes.cases import bp as cases_bp
from backend.routes.investigations import bp as investigations_bp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")


def create_app():
    app = Flask(__name__)
    init_database(app)
    app.register_blueprint(cases_bp)
    app.register_blueprint(investigations_bp)

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND, "index.html")

    @app.get("/css/<path:name>")
    def css(name):
        return send_from_directory(os.path.join(FRONTEND, "css"), name)

    @app.get("/js/<path:name>")
    def js(name):
        return send_from_directory(os.path.join(FRONTEND, "js"), name)

    @app.get("/api/health")
    def health():
        try:
            mongo.cx.admin.command("ping")
            return jsonify(status="ok", database=mongo.db.name)
        except PyMongoError:
            return jsonify(status="error", message="MongoDB is unavailable."), 503

    @app.errorhandler(404)
    def not_found(error):
        if os.path.basename(os.path.dirname(getattr(error, "description", ""))) == "api":
            return jsonify(error="API route not found."), 404
        return jsonify(error="Not found."), 404

    @app.errorhandler(PyMongoError)
    def database_error(error):
        app.logger.exception("MongoDB request failed")
        return jsonify(error="The database could not complete that request. Check MongoDB is running."), 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
