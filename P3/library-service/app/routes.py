from datetime import datetime
from pymongo import ReturnDocument
from quart import Blueprint, jsonify, request
from .mongodb_client import books_collection

library = Blueprint("library", __name__)


# Alta de un nuevo libro en la biblioteca
@library.route("/library/books", methods=["POST"])
async def create_book():
    # Leemos los datos JSON enviados por el cliente
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Cuerpo JSON invalido o vacio"}), 400

    isbn = data.get("isbn")
    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    publisher = data.get("publisher")
    available_stock = data.get("available_stock")

    # Comprobamos year y available_stock con "is None" porque un stock de 0 es valido
    if not isbn or not title or not author or not publisher or year is None or available_stock is None:
        return jsonify({"error": "Faltan campos obligatorios del libro"}), 400

    if available_stock < 0:
        return jsonify({"error": "available_stock no puede ser negativo"}), 400

    # Verificamos que no exista otro libro con el mismo ISBN
    existing = await books_collection.find_one({"isbn": isbn})
    if existing:
        return jsonify({"error": "Ya existe un libro con ese ISBN"}), 409

    # Construimos el documento del libro con el historial de prestamos vacio
    new_book = {
        "isbn": isbn,
        "title": title,
        "author": author,
        "year": year,
        "publisher": publisher,
        "available_stock": available_stock,
        "loan_history": []
    }

    await books_collection.insert_one(new_book)
    # Quitamos _id porque ObjectId no se puede convertir directamente a JSON
    new_book.pop("_id", None)

    return jsonify(new_book), 201


# Listado de libros cuyo stock disponible es 0
@library.route("/library/books/out-of-stock", methods=["GET"])
async def get_out_of_stock_books():
    cursor = books_collection.find({"available_stock": 0}, {"_id": 0})
    books = await cursor.to_list(length=None)
    return jsonify(books), 200


# Consulta de un libro concreto por su ISBN
@library.route("/library/books/<isbn>", methods=["GET"])
async def get_book(isbn):
    book = await books_collection.find_one({"isbn": isbn}, {"_id": 0})
    if not book:
        return jsonify({"error": "Libro no encontrado"}), 404

    return jsonify(book), 200


# Borrado de un libro si no tiene prestamos activos
@library.route("/library/books/<isbn>", methods=["DELETE"])
async def delete_book(isbn):
    book = await books_collection.find_one({"isbn": isbn}, {"_id": 0})
    if not book:
        return jsonify({"error": "Libro no encontrado"}), 404

    # Recorremos el historial para comprobar si queda algun prestamo sin devolver
    has_active_loans = False
    for loan in book.get("loan_history", []):
        if loan.get("return_date") is None:
            has_active_loans = True
            break

    if has_active_loans:
        return jsonify({"error": "No se puede borrar un libro con prestamos activos"}), 409

    # Eliminamos el libro de la coleccion
    await books_collection.delete_one({"isbn": isbn})
    return jsonify({"message": "Libro eliminado correctamente"}), 200


# Prestamo de un libro para el usuario autenticado
@library.route("/library/books/<isbn>/borrow", methods=["POST"])
async def borrow_book(isbn):
    # Obtenemos el usuario desde la cabecera que inyecta Nginx
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    now = datetime.now().isoformat()

    # Restamos stock y añadimos el prestamo de forma atomica para evitar condiciones de carrera
    updated_book = await books_collection.find_one_and_update(
        {
            "isbn": isbn,
            "available_stock": {"$gt": 0}
        },
        {
            "$inc": {"available_stock": -1},
            "$push": {
                "loan_history": {
                    "user_id": user_id,
                    "loan_date": now,
                    "return_date": None
                }
            }
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER
    )

    # Si no se actualizo, comprobamos si es porque no existe el libro o porque no hay stock
    if not updated_book:
        existing = await books_collection.find_one({"isbn": isbn})
        if not existing:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify({"error": "No hay stock disponible"}), 409

    return jsonify(updated_book), 200


# Devolucion de un libro prestado por el usuario autenticado
@library.route("/library/books/<isbn>/return", methods=["POST"])
async def return_book(isbn):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    now = datetime.now().isoformat()

    # Buscamos el prestamo activo de este usuario y lo cerramos de forma atomica
    updated_book = await books_collection.find_one_and_update(
        {
            "isbn": isbn,
            "loan_history": {
                "$elemMatch": {
                    "user_id": user_id,
                    "return_date": None
                }
            }
        },
        {
            "$inc": {"available_stock": 1},
            "$set": {"loan_history.$.return_date": now}
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER
    )

    # Distinguimos entre libro inexistente (404) y usuario sin prestamo activo (409)
    if not updated_book:
        existing = await books_collection.find_one({"isbn": isbn})
        if not existing:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify({"error": "No tienes un prestamo activo de este libro"}), 409

    return jsonify(updated_book), 200


# Listado de libros que el usuario tiene prestados actualmente
@library.route("/library/loans/active", methods=["GET"])
async def get_active_loans():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # Filtramos libros donde este usuario tenga un prestamo con return_date a None
    cursor = books_collection.find(
        {
            "loan_history": {
                "$elemMatch": {
                    "user_id": user_id,
                    "return_date": None
                }
            }
        },
        {"_id": 0}
    )
    active_books = await cursor.to_list(length=None)
    return jsonify(active_books), 200


# Historico completo de libros prestados al usuario (activos y devueltos)
@library.route("/library/loans/history", methods=["GET"])
async def get_loan_history():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # Buscamos todos los libros en cuyo historial aparezca el usuario
    cursor = books_collection.find(
        {"loan_history.user_id": user_id},
        {"_id": 0}
    )
    history_books = await cursor.to_list(length=None)
    return jsonify(history_books), 200
