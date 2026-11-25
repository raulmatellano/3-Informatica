import json
from quart import Quart
from .routes import library
from .mongodb_client import books_collection, mongo_client

# Creamos la aplicacion Quart y registramos las rutas de la biblioteca
app = Quart(__name__)
app.register_blueprint(library)


# Al arrancar cargamos los libros iniciales de populate.json si la coleccion esta vacia
@app.before_serving
async def startup():
    if await books_collection.count_documents({}) == 0:
        with open("app/populate.json", "r", encoding="utf-8") as f:
            books = json.load(f)

        if books:
            await books_collection.insert_many(books)


# Cerramos el cliente de MongoDB al apagar el servidor
@app.after_serving
async def shutdown():
    await mongo_client.close()
