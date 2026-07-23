from pymongo import MongoClient

from app.config import MONGO_DB_NAME, MONGO_URI

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[MONGO_DB_NAME]


def get_db():
    return db
