from quart import Blueprint, jsonify, request
from app.mongodb_client import books_collection

from datetime import datetime, timezone
from pymongo import ReturnDocument

# Creamos el Blueprint para agrupar todas las rutas de la biblioteca
library = Blueprint("library", __name__)
# ==============================================================================
# ENDPOINT 1: CREAR UN LIBRO (POST /library/books)
# ==============================================================================
@library.route("/library/books", methods=["POST"])
async def create_book():

    # 1. RECIBIR: leer el JSON del cuerpo (lleva await porque es el cuerpo)
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Cuerpo JSON inválido o vacío"}), 400

    # Extraemos los campos obligatorios que marca el enunciado
    isbn = data.get("isbn")
    title = data.get("title")
    author = data.get("author")
    year = data.get("year")
    publisher = data.get("publisher")
    available_stock = data.get("available_stock")

    # 2. VALIDAR: comprobar que no falte ningún campo obligatorio
    # Ojo: para year y available_stock usamos "is None" porque un stock de 0 es válido
    # (si pusiéramos "not available_stock", el número 0 se trataría como False).
    if not all([isbn, title, author, publisher]) or year is None or available_stock is None:
        return jsonify({"error": "Faltan campos obligatorios del libro"}), 400

    if not isinstance(year, int) or not isinstance(available_stock, int) or available_stock < 0:
        return jsonify({"error": "year debe ser entero y available_stock un entero >= 0"}), 400

    # 3. OPERAR EN MONGODB: comprobar que no exista ya ese ISBN e insertar el libro
    existing = await books_collection.find_one({"isbn": isbn})
    if existing:
        return jsonify({"error": "Ya existe un libro con ese ISBN"}), 409

    # Montamos el documento exactamente con los nombres de campo del enunciado.
    # El enunciado exige que loan_history empiece como un array vacío [].
    new_book = {
        "isbn": isbn,
        "title": title,
        "author": author,
        "year": year,
        "publisher": publisher,
        "available_stock": available_stock,
        "loan_history": []
    }

    # Guardamos el documento en la colección "books"
    await books_collection.insert_one(new_book)

    # Quitamos el campo "_id" que MongoDB añade automáticamente al diccionario new_book
    # porque ese tipo de dato (ObjectId) no se puede convertir a JSON.
    new_book.pop("_id", None)

    # 4. RESPONDER: código 201 (Created) con los datos del libro creado
    return jsonify(new_book), 201




# ==============================================================================
# ENDPOINT 2: BORRAR UN LIBRO (DELETE /library/books/<isbn>)
# No permite borrarlo si tiene algún préstamo activo (return_date == None).
# ==============================================================================
@library.route("/library/books/<isbn>", methods=["DELETE"])
async def delete_book(isbn):

    # 3. OPERAR EN MONGODB: primero buscamos el libro para ver si existe y revisar préstamos
    book = await books_collection.find_one({"isbn": isbn}, {"_id": 0})

    if not book:
        return jsonify({"error": "Libro no encontrado"}), 404

    # Comprobamos si algún préstamo de su historial sigue activo (return_date es None)
    has_active_loans = False

    for loan in book.get("loan_history", []):
        if loan.get("return_date") is None:
            has_active_loans = True
            break
    if has_active_loans:
        return jsonify({"error": "No se puede borrar un libro con préstamos activos"}), 409

    # Si no tiene préstamos activos, lo borramos de MongoDB
    await books_collection.delete_one({"isbn": isbn})

    # 4. RESPONDER: código 200 confirmando el borrado
    return jsonify({"message": "Libro eliminado correctamente"}), 200


# ==============================================================================
# ENDPOINT 3: CONSULTAR UN LIBRO POR ISBN (GET /library/books/<isbn>)
# ==============================================================================
# Fíjate en <isbn> en la ruta: Quart captura lo que escriba el cliente en la URL
# y te lo pasa automáticamente como parámetro "isbn" a la función.
@library.route("/library/books/<isbn>", methods=["GET"])
async def get_book(isbn):

    # 1 y 2. RECIBIR / VALIDAR: ya tenemos "isbn" directamente de la URL.

    # 3. OPERAR EN MONGODB: buscar el libro por su isbn.
    # {"_id": 0} le dice a MongoDB: "tráeme todo el documento MENOS el campo _id".
    book = await books_collection.find_one({"isbn": isbn}, {"_id": 0})

    if not book:
        return jsonify({"error": "Libro no encontrado"}), 404

    # 4. RESPONDER: devolvemos el libro completo (incluyendo su loan_history) y 200
    return jsonify(book), 200


# ==============================================================================
# ENDPOINT 4: LIBROS SIN STOCK (GET /library/books/out-of-stock)
# Devuelve una lista con todos los libros cuyo available_stock sea 0.
# ==============================================================================
@library.route("/library/books/out-of-stock", methods=["GET"])
async def get_out_of_stock_books():

    # find() no lleva await porque solo prepara la búsqueda (devuelve un cursor).
    # El await va en to_list(length=None), que trae todos los resultados en una lista.
    cursor = books_collection.find({"available_stock": 0}, {"_id": 0})
    books = await cursor.to_list(length=None)

    return jsonify(books), 200


# ==============================================================================
# ENDPOINT 5: PRÉSTAMOS ACTIVOS DEL USUARIO (GET /library/loans/active)
# Devuelve los libros que el usuario autenticado tiene prestados actualmente.
# ==============================================================================
@library.route("/library/loans/active", methods=["GET"])
async def get_active_loans():

    # Leemos el usuario que Nginx nos pasa en la cabecera X-User-Id
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # $elemMatch obliga a que el MISMO préstamo dentro de loan_history
    # tenga ese user_id Y return_date igual a None.
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


# ==============================================================================
# ENDPOINT 6: HISTÓRICO DE PRÉSTAMOS DEL USUARIO (GET /library/loans/history)
# Devuelve todos los libros que el usuario ha tomado prestados (activos y devueltos).
# ==============================================================================
@library.route("/library/loans/history", methods=["GET"])
async def get_loan_history():

    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # Aquí basta con buscar que user_id aparezca en cualquier elemento de loan_history
    cursor = books_collection.find(
        {"loan_history.user_id": user_id},
        {"_id": 0}
    )
    history_books = await cursor.to_list(length=None)

    return jsonify(history_books), 200



@library.route("/library/books/<isbn>/borrow", methods=["POST"])
async def borrow_book(isbn):

    # 1. Leer el usuario que nos pasa Nginx
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # 2. Fecha y hora actual en formato texto estándar (ej: "2026-11-22T16:06:00+00:00")
    now = datetime.now(timezone.utc).isoformat()

    # 3. Buscar el libro con stock > 0 y actualizarlo en un solo paso
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

    # 4. Si devuelve None: o el libro no existe (404) o estaba sin stock (409)
    if not updated_book:
        existing = await books_collection.find_one({"isbn": isbn})
        if not existing:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify({"error": "No hay stock disponible"}), 409

    # 5. Devolver el libro ya modificado
    return jsonify(updated_book), 200








@library.route("/library/books/<isbn>/return", methods=["POST"])
async def return_book(isbn):

    # 1. Leer el usuario que nos pasa Nginx
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "Cabecera X-User-Id no proporcionada"}), 401

    # 2. Fecha y hora exacta de la devolución
    now = datetime.now(timezone.utc).isoformat()

    # 3. Buscar el libro donde este usuario tenga un préstamo activo y cerrarlo
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

    # 4. Si devuelve None: o el libro no existe (404) o este usuario no lo tenía prestado (409)
    if not updated_book:
        existing = await books_collection.find_one({"isbn": isbn})
        if not existing:
            return jsonify({"error": "Libro no encontrado"}), 404
        return jsonify({"error": "No tienes un préstamo activo de este libro"}), 409

    # 5. Devolver el libro actualizado
    return jsonify(updated_book), 200