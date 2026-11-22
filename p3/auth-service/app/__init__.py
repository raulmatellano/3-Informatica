from quart import Quart
from app.routes import auth
from app.redis_client import redis_client

app = Quart(__name__)
app.register_blueprint(auth)


# Cierra la conexión con Redis limpiamente cuando se apaga el contenedor
@app.after_serving
async def shutdown():
    await redis_client.aclose()