from quart import Quart
from .routes import auth
from .redis_client import redis_client

# Creamos la aplicacion Quart y registramos las rutas de autenticacion
app = Quart(__name__)
app.register_blueprint(auth)


# Cerramos la conexion con Redis al apagar el servidor
@app.after_serving
async def shutdown():
    await redis_client.aclose()
