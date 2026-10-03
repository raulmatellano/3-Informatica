import os
import json
import uuid
import hashlib
from quart import Quart, request, jsonify

app = Quart(__name__)

# Secreto compartido entre user.py y file.py para validar tokens
SECRET_UUID = uuid.UUID("5624da4e-a64c-4943-b5d5-67ced4d90171")

# Configuramos la carpeta donde guardaremos los archivos JSON de los usuarios
DIR_USUARIOS = "almacenamiento/usuarios"
os.makedirs(DIR_USUARIOS, exist_ok=True)


def hashear(texto: str) -> str:
    """Encripta texto usando SHA-256."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def generate_token(user_uid: str) -> str:
    """Genera el token de acceso mezclando el secreto y el UID del usuario."""
    return str(uuid.uuid5(SECRET_UUID, str(user_uid)))


# -------------------------------------------------------------
# RUTA 1: CREAR USUARIO (PUT /user)
# -------------------------------------------------------------
@app.put("/user")
async def create_user():
    data = await request.get_json()
    if not data or "name" not in data or "password" not in data:
        return jsonify({"error": "Faltan datos (name o password)"}), 400

    name = data["name"]
    ruta_archivo = f"{DIR_USUARIOS}/{name}.json"

    # Comprobamos si el archivo de este usuario ya existe
    if os.path.exists(ruta_archivo):
        return jsonify({"error": "El usuario ya existe"}), 409

    # Generamos UID único y ciframos la contraseña
    new_uid = str(uuid.uuid4())
    pass_hash = hashear(data["password"])

    # Guardamos al usuario en su propio archivo JSON
    # Guardamos también el name dentro para facilitar las cosas
    usuario_datos = {"name": name, "uid": new_uid, "password_hash": pass_hash}
    with open(ruta_archivo, "w") as f:
        json.dump(usuario_datos, f)

    # Generamos el token y devolvemos UID y token (Código 201)
    token = generate_token(new_uid)
    return jsonify({"uid": new_uid, "token": token}), 201


# -------------------------------------------------------------
# RUTA 2: INICIAR SESIÓN (POST /user)
# -------------------------------------------------------------
@app.post("/user")
async def login():
    data = await request.get_json()
    if not data or "name" not in data or "password" not in data:
        return jsonify({"error": "Faltan datos"}), 400

    ruta_archivo = f"{DIR_USUARIOS}/{data['name']}.json"

    # Comprobar si el archivo del usuario existe
    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Leemos el archivo
    with open(ruta_archivo, "r") as f:
        usuario_datos = json.load(f)

    # Comprobamos la contraseña
    if hashear(data["password"]) != usuario_datos["password_hash"]:
        return jsonify({"error": "Contraseña incorrecta"}), 401

    user_uid = usuario_datos["uid"]
    token = generate_token(user_uid)
    return jsonify({"uid": user_uid, "token": token}), 200


# -------------------------------------------------------------
# RUTA 3: CAMBIAR CONTRASEÑA (PATCH /user)
# -------------------------------------------------------------
@app.patch("/user")
async def update_password():
    # 1. Miramos el token de la cabecera
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Falta cabecera Authorization"}), 401
    token_recibido = auth_header.replace("Bearer ", "").strip()

    # 2. Leemos SOLO la nueva contraseña (como dice la tabla del PDF)
    data = await request.get_json()
    if not data or "password" not in data:
        return jsonify({"error": "Falta el campo password"}), 400

    nueva_password = data["password"]
    usuario_encontrado = None
    ruta_del_archivo_encontrado = None

    # 3. Buscamos qué archivo de usuario corresponde a este token
    # Recorremos todos los archivos de la carpeta
    for nombre_archivo in os.listdir(DIR_USUARIOS):
        ruta_temp = f"{DIR_USUARIOS}/{nombre_archivo}"
        with open(ruta_temp, "r") as f:
            datos_temp = json.load(f)
            
            # Si el token que nos dan coincide con el de este archivo, lo hemos encontrado
            if generate_token(datos_temp["uid"]) == token_recibido:
                usuario_encontrado = datos_temp
                ruta_del_archivo_encontrado = ruta_temp
                break # Rompemos el bucle porque ya lo encontramos

    if not usuario_encontrado:
        return jsonify({"error": "Token inválido"}), 401

    # 4. Guardamos el cambio en el archivo correcto
    usuario_encontrado["password_hash"] = hashear(nueva_password)
    with open(ruta_del_archivo_encontrado, "w") as f:
        json.dump(usuario_encontrado, f)

    return jsonify({"mensaje": "Contraseña cambiada con éxito"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)