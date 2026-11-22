# ==============================================================================
# IMPORTS (las "cajas de herramientas" que vamos a usar)
# ==============================================================================

# 1. secrets: viene incluido en Python. Sirve para generar códigos aleatorios
#    seguros (lo usaremos para fabricar el token de sesión).
import secrets

# 2. quart: es nuestro framework web asíncrono. Sacamos 3 herramientas:
#    - Blueprint: permite agrupar rutas en este archivo para luego conectarlas en __init__.py.
#    - request: guarda todo lo que el cliente nos acaba de enviar (JSON, cabeceras, etc.).
#    - jsonify: convierte un diccionario de Python en una respuesta HTTP en formato JSON.
from quart import Blueprint, request, jsonify

# 3. werkzeug.security: se instala automáticamente junto con Quart. Sacamos 2 funciones:
#    - generate_password_hash: cifra una contraseña en texto plano para guardarla segura.
#    - check_password_hash: comprueba si una contraseña coincide con el hash guardado.
from werkzeug.security import generate_password_hash, check_password_hash

# 4. .redis_client: es nuestro propio archivo redis_client.py (el punto "." significa
#    "búscalo en esta misma carpeta app/"). Importamos la conexión asíncrona a Redis.
from .redis_client import redis_client


# ==============================================================================
# CONFIGURACIÓN INICIAL
# ==============================================================================

# Gracias a: Blueprint (de quart)
# Estructura: variable = Blueprint("nombre_interno", __name__)
# Crea el grupo de rutas que luego importaremos en __init__.py
auth = Blueprint("auth", __name__)

# Tiempo de vida (TTL) de los tokens de sesión: 5 minutos = 300 segundos
TTL = 300


# ==============================================================================
# ENDPOINT 1: REGISTRO DE USUARIOS (POST /auth/register)
# ==============================================================================

# Gracias a: Blueprint (de quart)
# Estructura: @nombre_blueprint.route("/ruta", methods=["MÉTODO_HTTP"])
# Conecta la URL "/auth/register" (cuando llega por POST) con la función de abajo.
@auth.route("/auth/register", methods=["POST"])
async def register():  # "async def" es obligatorio en Quart para poder usar "await" dentro

    # Gracias a: request (de quart)
    # Estructura: variable = await request.get_json()
    # Lee el cuerpo JSON que envió el cliente y lo convierte en un diccionario Python.
    data = await request.get_json()

    if not data:
        # Gracias a: jsonify (de quart)
        # Estructura: return jsonify(diccionario), codigo_http
        # Devuelve un JSON de error con código 400 (petición mal formada).
        return jsonify({"error": "Faltan datos"}), 400

    # Método estándar de diccionarios en Python: diccionario.get("clave")
    # Devuelve el valor si existe, o None si el cliente no lo envió (evita que crashee).
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        return jsonify({"error": "username, password y email son obligatorios"}), 400

    # Formato obligatorio del enunciado para usuarios: "user:{username}"
    user_key = f"user:{username}"

    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: await redis_client.exists("clave")
    # Devuelve 1 (True) si la clave ya existe en Redis, o 0 (False) si no existe.
    if await redis_client.exists(user_key):
        # Código 409 (Conflict): el usuario ya estaba registrado
        return jsonify({"error": "El usuario ya existe"}), 409

    # Gracias a: generate_password_hash (de werkzeug.security)
    # Estructura: hash_resultante = generate_password_hash("contraseña_en_texto_plano")
    hashed_password = generate_password_hash(password)

    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: await redis_client.hset("clave", mapping={"campo1": valor1, "campo2": valor2})
    # Guarda un HASH (como un diccionario) en Redis. NO ponemos TTL porque los usuarios son permanentes.
    await redis_client.hset(
        user_key,
        mapping={
            "password_hash": hashed_password,
            "email": email,
        },
    )

    # Código 201 (Created): recurso creado con éxito
    return jsonify({"message": "Usuario registrado correctamente"}), 201


# ==============================================================================
# ENDPOINT 2: INICIO DE SESIÓN (POST /auth/login)
# ==============================================================================

@auth.route("/auth/login", methods=["POST"])
async def login():
    # Gracias a: request (de quart) -> lee el JSON enviado por el cliente
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400

    user_key = f"user:{username}"

    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: diccionario = await redis_client.hgetall("clave")
    # Recupera TODOS los campos del HASH guardado en Redis (ej: {"password_hash": "...", "email": "..."}).
    # Si la clave no existe, devuelve un diccionario vacío {}.
    user_data = await redis_client.hgetall(user_key)

    # Gracias a: check_password_hash (de werkzeug.security)
    # Estructura: check_password_hash(hash_guardado_en_bd, contraseña_recibida) -> True o False
    # Si el usuario no existe (not user_data) O la contraseña no coincide, devolvemos 401.
    if not user_data or not check_password_hash(user_data["password_hash"], password):
        return jsonify({"error": "Credenciales inválidas"}), 401

    # Gracias a: secrets (librería estándar de Python)
    # Estructura: secrets.token_hex(num_bytes)
    # Genera un texto aleatorio seguro (32 bytes = 64 caracteres hexadecimales).
    token = secrets.token_hex(32)

    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: await redis_client.set("clave", "valor", ex=segundos_de_vida)
    # Guarda un STRING en Redis con formato "session:{token}" apuntando al usuario.
    # El parámetro "ex=TTL" fija el TTL de 5 minutos para que caduque solo.
    await redis_client.set(f"session:{token}", username, ex=TTL)

    # Gracias a: jsonify (de quart) -> devuelve el token y código 200 (OK)
    return jsonify({"token": token}), 200



# ==============================================================================
# ENDPOINT 3: VALIDACIÓN DE TOKEN (GET /auth/validate)
# Llamado internamente por Nginx (auth_request) antes de dejar pasar a /library/*
# ==============================================================================

# Gracias a: Blueprint (de quart)
# Estructura: @nombre_blueprint.route("/ruta", methods=["GET"])
# Fíjate que aquí el método es GET (no POST), según la tabla del enunciado.
@auth.route("/auth/validate", methods=["GET"])
async def validate():

    # 1. RECIBIR: leer la cabecera "Authorization"
    # Gracias a: request (de quart)
    # Estructura: valor = request.headers.get("Nombre-Cabecera")
    # Nota: leer cabeceras NO lleva "await" (a diferencia de get_json()).
    # Si el cliente no mandó la cabecera, devuelve None.
    auth_header = request.headers.get("Authorization")

    # 2. VALIDAR FORMATO: debe existir y empezar exactamente por "Bearer "
    # Método estándar de textos en Python: texto.startswith("prefijo") -> True o False
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token no proporcionado o formato inválido"}), 401

    # Extraemos solo el token quitando la palabra "Bearer " del principio.
    token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        return jsonify({"error": "Token vacío"}), 401

    # 3. CONSULTAR REDIS: buscar si existe la sesión "session:{token}"
    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: valor = await redis_client.get("clave")
    # Como las sesiones se guardaron con .set() (STRING), se leen con .get().
    # Si el token existe y no ha caducado, devuelve el username (ej: "ana").
    # Si no existe o pasaron los 5 minutos, devuelve None.
    username = await redis_client.get(f"session:{token}")

    if not username:
        return jsonify({"error": "Token inválido o expirado"}), 401

    # 4. RESPONDER A NGINX: código 200 + cabecera X-User-Id con el username
    # Gracias a: jsonify (de quart)
    # Estructura con cabeceras: return cuerpo, codigo_http, {"Nombre-Cabecera": valor}
    # El 3er elemento es un diccionario con las cabeceras HTTP extra que queremos enviar.
    return jsonify({"username": username}), 200, {"X-User-Id": username}




# ==============================================================================
# ENDPOINT 4: CIERRE DE SESIÓN (POST /auth/logout)
# Invalida el token de inmediato borrándolo de Redis sin esperar al TTL.
# ==============================================================================

# Gracias a: Blueprint (de quart)
# Estructura: @nombre_blueprint.route("/ruta", methods=["POST"])
@auth.route("/auth/logout", methods=["POST"])
async def logout():

    # 1. RECIBIR: leer la cabecera "Authorization" (sin await, igual que en validate)
    # Gracias a: request (de quart)
    auth_header = request.headers.get("Authorization")

    # 2. VALIDAR FORMATO: si falta la cabecera o no es tipo Bearer -> 401
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token no proporcionado o formato inválido"}), 401

    # Quitamos "Bearer " del principio y limpiamos espacios sobrantes
    token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        return jsonify({"error": "Token vacío"}), 401

    # 3. OPERAR EN REDIS: borrar la clave "session:{token}" de inmediato
    # Gracias a: redis_client (de redis.asyncio)
    # Estructura: num_borradas = await redis_client.delete("clave")
    # Devuelve 1 si la clave existía y se borró, o 0 si no existía / caducó / ya se borró.
    deleted = await redis_client.delete(f"session:{token}")

    if deleted == 0:
        # 401 si el token es desconocido, ha caducado o ya se cerró sesión antes
        return jsonify({"error": "Token inválido, expirado o sesión ya cerrada"}), 401

    # 4. RESPONDER: código 200 si se eliminó correctamente
    # Gracias a: jsonify (de quart)
    return jsonify({"message": "Sesión cerrada correctamente"}), 200