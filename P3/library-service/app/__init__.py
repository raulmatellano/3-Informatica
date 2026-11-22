import json
import os
from datetime import datetime
from quart import Quart
from .mongodb_client import books_collection, db, mongo_client
from .routes import library_bp

app = Quart(__name__)
app.register_blueprint(library_bp)


def parsear_fecha_iso(cadena_fecha):
    if cadena_fecha is None:
        return None
    return datetime.fromisoformat(cadena_fecha)


async def poblar_base_datos():
    await books_collection.create_index("isbn", unique=True)

    total_libros = await books_collection.count_documents({})
    if total_libros > 0:
        return

    ruta_populate = os.path.join(os.path.dirname(__file__), "populate.json")
    with open(ruta_populate, "r", encoding="utf-8") as fichero:
        libros = json.load(fichero)

    for libro in libros:
        for prestamo in libro.get("loan_history", []):
            prestamo["loan_date"] = parsear_fecha_iso(prestamo.get("loan_date"))
            prestamo["return_date"] = parsear_fecha_iso(prestamo.get("return_date"))

    if libros:
        await books_collection.insert_many(libros)


@app.before_serving
async def startup():
    await db.command("ping")
    await poblar_base_datos()


@app.after_serving
async def shutdown():
    await mongo_client.close()