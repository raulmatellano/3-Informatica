import os
import json
import uuid
import hashlib
from quart import Quart, request, jsonify

app = Quart(__name__)

SECRET_UUID = uuid.UUID("5624da4e-a64c-4943-b5d5-67ced4d90171")

DIR_USUARIOS = "almacenamiento/usuarios"
os.makedirs(DIR_USUARIOS, exist_ok=True)


def hashear(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def generate_token(user_uid: str) -> str:
    return str(uuid.uuid5(SECRET_UUID, str(user_uid)))


@app.put("/user")
async def create_user():
    data = await request.get_json()
    if not data or "name" not in data or "password" not in data:
        return jsonify({"error": "Faltan datos (name o password)"}), 400

    name = data["name"]
    ruta_archivo = f"{DIR_USUARIOS}/{name}.json"

    if os.path.exists(ruta_archivo):
        return jsonify({"error": "El usuario ya existe"}), 409

    new_uid = str(uuid.uuid4())
    pass_hash = hashear(data["password"])

    usuario_datos = {"name": name, "uid": new_uid, "password_hash": pass_hash}
    with open(ruta_archivo, "w") as f:
        json.dump(usuario_datos, f)

    token = generate_token(new_uid)
    return jsonify({"uid": new_uid, "token": token}), 201


@app.post("/user")
async def login():
    data = await request.get_json()
    if not data or "name" not in data or "password" not in data:
        return jsonify({"error": "Faltan datos"}), 400

    ruta_archivo = f"{DIR_USUARIOS}/{data['name']}.json"

    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "Usuario no encontrado"}), 404

    with open(ruta_archivo, "r") as f:
        usuario_datos = json.load(f)

    if hashear(data["password"]) != usuario_datos["password_hash"]:
        return jsonify({"error": "Contraseña incorrecta"}), 401

    user_uid = usuario_datos["uid"]
    token = generate_token(user_uid)
    return jsonify({"uid": user_uid, "token": token}), 200


@app.patch("/user")
async def update_password():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Falta cabecera Authorization"}), 401
    token_recibido = auth_header.replace("Bearer ", "").strip()

    data = await request.get_json()
    if not data or "password" not in data:
        return jsonify({"error": "Falta el campo password"}), 400

    nueva_password = data["password"]
    usuario_encontrado = None
    ruta_del_archivo_encontrado = None

    for nombre_archivo in os.listdir(DIR_USUARIOS):
        ruta_temp = f"{DIR_USUARIOS}/{nombre_archivo}"
        with open(ruta_temp, "r") as f:
            datos_temp = json.load(f)
            
            if generate_token(datos_temp["uid"]) == token_recibido:
                usuario_encontrado = datos_temp
                ruta_del_archivo_encontrado = ruta_temp
                break

    if not usuario_encontrado:
        return jsonify({"error": "Token inválido"}), 401

    usuario_encontrado["password_hash"] = hashear(nueva_password)
    with open(ruta_del_archivo_encontrado, "w") as f:
        json.dump(usuario_encontrado, f)

    return jsonify({"mensaje": "Contraseña cambiada con éxito"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)