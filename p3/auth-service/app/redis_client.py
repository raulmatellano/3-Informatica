import os
import redis.asyncio as redis

# Leemos host y puerto desde variables de entorno (por defecto el contenedor "redis" y puerto 6379)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# decode_responses=True es clave: hace que Redis devuelva strings normales ("ana")
# en lugar de bytes (b"ana").
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)