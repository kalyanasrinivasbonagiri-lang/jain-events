import os

from dotenv import load_dotenv
from flask_pymongo import PyMongo

load_dotenv()
mongo = PyMongo()


def init_database(app):
    app.config["MONGO_URI"] = os.getenv(
        "MONGO_URI", "mongodb://localhost:27017/mystery_case_solver"
    )
    mongo.init_app(app)


def collections():
    return mongo.db.cases, mongo.db.investigations
