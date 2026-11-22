import os
import secrets
from quart import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from .redis_client import redis_client

SESSION_TTL = int(os.getenv("SESSION_TTL", "300"))

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def validar_campos_json(datos, campos_requeridos):
    if not isinstance(datos, dict):
        return False, "El cuerpo de la peticion debe ser un objeto JSON"

    for campo in campos_requeridos:
        valor = datos.get(campo)
        if not isinstance(valor, str) or valor.strip() == "":
            return False, f"El campo '{campo}' es obligatorio y debe ser texto no vacio"

    return True, None


def extraer_token_bearer():
    cabecera = request.headers.get("Authorization", "")
    partes = cabecera.split(" ")

    if len(partes) != 2 or partes[0] != "Bearer":
        return None

    token = partes[1].strip()
    if token == "":
        return None

    return token


@auth_bp.post("/register")
async def register():
    datos = await request.get_json(silent=True)
    valido, mensaje_error = validar_campos_json(datos, ["username", "password", "email"])
    if not valido:
        return jsonify({"error": mensaje_error}), 400

    username = datos["username"].strip()
    password = datos["password"]
    email = datos["email"].strip()

    clave_usuario = f"user:{username}"
    existe = await redis_client.exists(clave_usuario)
    if existe:
        return jsonify({"error": "El usuario ya existe"}), 409

    password_hash = generate_password_hash(password)
    await redis_client.hset(
        clave_usuario,
        mapping={
            "password_hash": password_hash,
            "email": email,
        },
    )

    return jsonify({"message": "Usuario registrado correctamente", "username": username}), 201


@auth_bp.post("/login")
async def login():
    datos = await request.get_json(silent=True)
    valido, mensaje_error = validar_campos_json(datos, ["username", "password"])
    if not valido:
        return jsonify({"error": mensaje_error}), 400

    username = datos["username"].strip()
    password = datos["password"]

    clave_usuario = f"user:{username}"
    datos_usuario = await redis_client.hgetall(clave_usuario)

    if not datos_usuario:
        return jsonify({"error": "Credenciales invalidas"}), 401

    password_hash = datos_usuario.get("password_hash", "")
    if not check_password_hash(password_hash, password):
        return jsonify({"error": "Credenciales invalidas"}), 401

    token = secrets.token_urlsafe(32)
    clave_sesion = f"session:{token}"
    await redis_client.set(clave_sesion, username, ex=SESSION_TTL)

    return jsonify({"token": token}), 200


@auth_bp.get("/validate")
async def validate():
    token = extraer_token_bearer()
    if token is None:
        return jsonify({"error": "Token ausente o con formato incorrecto"}), 401

    clave_sesion = f"session:{token}"
    username = await redis_client.get(clave_sesion)
    if username is None:
        return jsonify({"error": "Token invalido o caducado"}), 401

    respuesta = jsonify({"user_id": username})
    respuesta.headers["X-User-Id"] = username
    return respuesta, 200


@auth_bp.post("/logout")
async def logout():
    token = extraer_token_bearer()
    if token is None:
        return jsonify({"error": "Token ausente o con formato incorrecto"}), 401

    clave_sesion = f"session:{token}"
    eliminados = await redis_client.delete(clave_sesion)
    if eliminados == 0:
        return jsonify({"error": "Sesion no encontrada o ya cerrada"}), 401

    return jsonify({"message": "Sesion cerrada correctamente"}), 200