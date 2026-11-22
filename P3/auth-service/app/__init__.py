from quart import Quart
from .redis_client import redis_client
from .routes import auth_bp

app = Quart(__name__)
app.register_blueprint(auth_bp)


@app.before_serving
async def startup():
    await redis_client.ping()


@app.after_serving
async def shutdown():
    await redis_client.aclose()