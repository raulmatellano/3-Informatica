import os
from pymongo import AsyncMongoClient

# Leemos la URI y el nombre de la base de datos desde variables de entorno
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB", "library_db")

# Conectamos de forma asincrona con MongoDB y seleccionamos la coleccion books
mongo_client = AsyncMongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
books_collection = db["books"]
