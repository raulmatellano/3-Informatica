from datetime import datetime, timezone
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from quart import Blueprint, jsonify, request
from .mongodb_client import books_collection

library_bp = Blueprint("library", __name__, url_prefix="/library")


def obtener_usuario_autenticado():
    user_id = request.headers.get("X-User-Id", "").strip()
    if user_id == "":
        return None
    return user_id


def formatear_fecha(fecha):
    if isinstance(fecha, datetime):
        return fecha.isoformat().replace("+00:00", "Z")
    return fecha


def serializar_libro(documento, filtrar_usuario=None):
    historial_serializado = []

    for prestamo in documento.get("loan_history", []):
        if filtrar_usuario is not None and prestamo.get("user_id") != filtrar_usuario:
            continue

        historial_serializado.append(
            {
                "user_id": prestamo.get("user_id"),
                "loan_date": formatear_fecha(prestamo.get("loan_date")),
                "return_date": formatear_fecha(prestamo.get("return_date")),
            }
        )

    return {
        "isbn": documento["isbn"],
        "title": documento["title"],
        "author": documento["author"],
        "year": documento["year"],
        "publisher": documento["publisher"],
        "available_stock": documento["available_stock"],
        "loan_history": historial_serializado,
    }


def validar_datos_libro(datos):
    if not isinstance(datos, dict):
        return False, "El cuerpo de la peticion debe ser un objeto JSON"

    campos_texto = ["isbn", "title", "author", "publisher"]
    for campo in campos_texto:
        valor = datos.get(campo)
        if not isinstance(valor, str) or valor.strip() == "":
            return False, f"El campo '{campo}' es obligatorio y debe ser texto no vacio"

    year = datos.get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        return False, "El campo 'year' debe ser un numero entero"

    stock = datos.get("available_stock")
    if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0:
        return False, "El campo 'available_stock' debe ser un entero mayor o igual que 0"

    return True, None


@library_bp.post("/books")
async def create_book():
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    datos = await request.get_json(silent=True)
    valido, mensaje_error = validar_datos_libro(datos)
    if not valido:
        return jsonify({"error": mensaje_error}), 400

    nuevo_libro = {
        "isbn": datos["isbn"].strip(),
        "title": datos["title"].strip(),
        "author": datos["author"].strip(),
        "year": datos["year"],
        "publisher": datos["publisher"].strip(),
        "available_stock": datos["available_stock"],
        "loan_history": [],
    }

    try:
        await books_collection.insert_one(nuevo_libro)
    except DuplicateKeyError:
        return jsonify({"error": "Ya existe un libro con ese ISBN"}), 409

    return jsonify(serializar_libro(nuevo_libro)), 201


@library_bp.get("/books/out-of-stock")
async def get_out_of_stock_books():
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    cursor = books_collection.find({"available_stock": {"$lte": 0}})
    libros_sin_stock = []

    async for documento in cursor:
        libros_sin_stock.append(serializar_libro(documento))

    return jsonify(libros_sin_stock), 200


@library_bp.get("/books/<isbn>")
async def get_book(isbn):
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    documento = await books_collection.find_one({"isbn": isbn})
    if documento is None:
        return jsonify({"error": "Libro no encontrado"}), 404

    return jsonify(serializar_libro(documento)), 200


@library_bp.delete("/books/<isbn>")
async def delete_book(isbn):
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    resultado = await books_collection.delete_one(
        {
            "isbn": isbn,
            "loan_history": {
                "$not": {
                    "$elemMatch": {"return_date": None}
                }
            },
        }
    )

    if resultado.deleted_count == 1:
        return jsonify({"message": "Libro eliminado correctamente"}), 200

    existe = await books_collection.find_one({"isbn": isbn}, {"_id": 1})
    if existe is not None:
        return jsonify({"error": "No se puede borrar un libro con prestamos activos"}), 409

    return jsonify({"error": "Libro no encontrado"}), 404


@library_bp.post("/books/<isbn>/borrow")
async def borrow_book(isbn):
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    ahora_utc = datetime.now(timezone.utc)
    nuevo_prestamo = {
        "user_id": user_id,
        "loan_date": ahora_utc,
        "return_date": None,
    }

    libro_actualizado = await books_collection.find_one_and_update(
        {
            "isbn": isbn,
            "available_stock": {"$gt": 0},
        },
        {
            "$inc": {"available_stock": -1},
            "$push": {"loan_history": nuevo_prestamo},
        },
        return_document=ReturnDocument.AFTER,
    )

    if libro_actualizado is None:
        existe = await books_collection.find_one({"isbn": isbn}, {"_id": 1})
        if existe is not None:
            return jsonify({"error": "No hay stock disponible para este libro"}), 409
        return jsonify({"error": "Libro no encontrado"}), 404

    return jsonify(serializar_libro(libro_actualizado)), 200


@library_bp.post("/books/<isbn>/return")
async def return_book(isbn):
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    ahora_utc = datetime.now(timezone.utc)

    libro_actualizado = await books_collection.find_one_and_update(
        {
            "isbn": isbn,
            "loan_history": {
                "$elemMatch": {
                    "user_id": user_id,
                    "return_date": None,
                }
            },
        },
        {
            "$inc": {"available_stock": 1},
            "$set": {"loan_history.$.return_date": ahora_utc},
        },
        return_document=ReturnDocument.AFTER,
    )

    if libro_actualizado is None:
        existe = await books_collection.find_one({"isbn": isbn}, {"_id": 1})
        if existe is None:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify({"error": "No tienes ningun prestamo activo de este libro"}), 409

    return jsonify(serializar_libro(libro_actualizado)), 200


@library_bp.get("/loans/active")
async def get_active_loans():
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    cursor = books_collection.find(
        {
            "loan_history": {
                "$elemMatch": {
                    "user_id": user_id,
                    "return_date": None,
                }
            }
        }
    )

    prestamos_activos = []
    async for documento in cursor:
        prestamos_activos.append(serializar_libro(documento, filtrar_usuario=user_id))

    return jsonify(prestamos_activos), 200


@library_bp.get("/loans/history")
async def get_loans_history():
    user_id = obtener_usuario_autenticado()
    if user_id is None:
        return jsonify({"error": "Usuario no autenticado"}), 401

    cursor = books_collection.find({"loan_history.user_id": user_id})

    historial_usuario = []
    async for documento in cursor:
        historial_usuario.append(serializar_libro(documento, filtrar_usuario=user_id))

    return jsonify(historial_usuario), 200