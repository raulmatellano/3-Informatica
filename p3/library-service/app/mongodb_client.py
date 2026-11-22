import os
# Gracias a: pymongo (librería oficial exigida en el enunciado)
from pymongo import AsyncMongoClient

# Leemos la dirección de MongoDB desde variables de entorno (para que sea flexible en docker-compose).
#os.getenv("NOMBRE", "valor_por_defecto") 27017: Es el puerto por defecto de MongoDB en todo el mundo (igual que 6379 es el puerto por defecto de Redis o 80 el de HTTP).
# "mongodb" será el nombre del contenedor de la base de datos en docker-compose.yml.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB", "library_db")

# 1. Creamos el cliente asíncrono de MongoDB
mongo_client = AsyncMongoClient(MONGO_URI)

# 2. Seleccionamos la base de datos y la colección "books" (nombre obligatorio del enunciado)
db = mongo_client[MONGO_DB]
books_collection = db["books"]