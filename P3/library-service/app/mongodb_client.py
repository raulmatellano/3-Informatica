import os
from pymongo import AsyncMongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB", "library_db")

mongo_client = AsyncMongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
books_collection = db["books"]