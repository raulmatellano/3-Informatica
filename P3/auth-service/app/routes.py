import secrets
from quart import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .redis_client import redis_client

auth = Blueprint("auth", __name__)

# Tiempo de expiracion de las sesiones en segundos (5 minutos)
TTL = 300


# Registro de nuevos usuarios en Redis
@auth.route("/auth/register", methods=["POST"])
async def register():
    # Leemos el JSON recibido en la peticion
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        return jsonify({"error": "username, password y email son obligatorios"}), 400

    # Comprobamos si el usuario ya estaba registrado
    user_key = f"user:{username}"
    if await redis_client.exists(user_key):
        return jsonify({"error": "El usuario ya existe"}), 409

    # Ciframos la contraseña y guardamos el usuario de forma permanente como hash
    hashed_password = generate_password_hash(password)
    user_fields = {"password_hash": hashed_password, "email": email}
    await redis_client.hset(user_key, mapping=user_fields)  # type: ignore

    return jsonify({"message": "Usuario registrado correctamente"}), 201


# Inicio de sesion y generacion del token temporal
@auth.route("/auth/login", methods=["POST"])
async def login():
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Faltan datos"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400

    # Recuperamos los datos del usuario desde Redis y verificamos la contraseña
    user_key = f"user:{username}"
    user_data = await redis_client.hgetall(user_key)  # type: ignore

    if not user_data or not check_password_hash(user_data["password_hash"], password):
        return jsonify({"error": "Credenciales invalidas"}), 401

    # Generamos un token aleatorio y lo guardamos en Redis con TTL
    token = secrets.token_hex(32)
    await redis_client.set(f"session:{token}", username, ex=TTL)

    return jsonify({"token": token}), 200


# Validacion interna del token usada por Nginx (auth_request)
@auth.route("/auth/validate", methods=["GET"])
async def validate():
    # Extraemos la cabecera Authorization y comprobamos que tenga formato Bearer
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token no proporcionado o formato invalido"}), 401

    token = auth_header[7:].strip()
    if not token:
        return jsonify({"error": "Token vacio"}), 401

    # Buscamos si existe una sesion activa para ese token
    username = await redis_client.get(f"session:{token}")
    if not username:
        return jsonify({"error": "Token invalido o expirado"}), 401

    # Devolvemos 200 y la cabecera X-User-Id para que Nginx identifique al usuario
    return jsonify({"username": username}), 200, {"X-User-Id": username}


# Cierre de sesion eliminando el token de Redis
@auth.route("/auth/logout", methods=["POST"])
async def logout():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token no proporcionado o formato invalido"}), 401

    token = auth_header[7:].strip()
    if not token:
        return jsonify({"error": "Token vacio"}), 401

    # Borramos la clave de sesion para invalidar el token al instante
    deleted = await redis_client.delete(f"session:{token}")
    if deleted == 0:
        return jsonify({"error": "Token invalido o sesion ya cerrada"}), 401

    return jsonify({"message": "Sesion cerrada correctamente"}), 200
