import os
import redis.asyncio as redis

# Leemos host y puerto de Redis desde las variables de entorno
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Creamos el cliente asincrono devolviendo strings en vez de bytes
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)
