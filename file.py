import os
import json
import uuid
import aiofiles
from quart import Quart, request, jsonify

app = Quart(__name__)

# Mismo secreto que en user.py
SECRET_UUID = uuid.UUID("5624da4e-a64c-4943-b5d5-67ced4d90171")

# Carpeta base para los ficheros
DIR_FICHEROS = "almacenamiento/ficheros"
os.makedirs(DIR_FICHEROS, exist_ok=True)


def verificar_token(uid: str, auth_header: str) -> bool:
    """Verifica si el token en la cabecera pertenece al UID proporcionado."""
    if not auth_header:
        return False
    token_recibido = auth_header.replace("Bearer ", "").strip()
    token_esperado = str(uuid.uuid5(SECRET_UUID, str(uid)))
    return token_recibido == token_esperado


# -------------------------------------------------------------
# RUTA 1: LISTAR DOCUMENTOS (GET /file/<uid>)
# -------------------------------------------------------------
@app.get("/file/<uid>")
async def listar_documentos(uid):
    # 1. Verificar autenticación (solo el dueño puede listar)
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    if not os.path.exists(ruta_usuario):
        # Si no existe la carpeta, significa que aún no ha subido nada
        return jsonify({"ficheros": []}), 200

    # 2. Listar archivos excluyendo los .meta
    archivos = os.listdir(ruta_usuario)
    documentos = [f for f in archivos if not f.endswith(".meta")]

    return jsonify({"ficheros": documentos}), 200


# -------------------------------------------------------------
# RUTA 2: CREAR O REEMPLAZAR DOCUMENTO (PUT /file/<uid>/<filename>)
# -------------------------------------------------------------
@app.put("/file/<uid>/<filename>")
async def crear_o_actualizar_documento(uid, filename):
    # 1. Verificar autenticación
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    # 2. Obtener datos. Esperamos un JSON con {"content": "texto del archivo"}
    datos = await request.get_json()
    if not datos or "content" not in datos:
        return jsonify({"error": "Falta el campo 'content' en el JSON"}), 400

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    os.makedirs(ruta_usuario, exist_ok=True)

    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"
    
    es_nuevo = not os.path.exists(ruta_txt)

    # 3. Guardar el archivo de texto de forma asíncrona
    async with aiofiles.open(ruta_txt, "w") as f:
        await f.write(datos["content"])

    # 4. Si es nuevo, crear archivo meta por defecto (privado)
    if es_nuevo:
        async with aiofiles.open(ruta_meta, "w") as f:
            await f.write(json.dumps({"public": False}))
            
    codigo_respuesta = 201 if es_nuevo else 200
    return jsonify({"mensaje": "Archivo guardado con éxito"}), codigo_respuesta


# -------------------------------------------------------------
# RUTA 3: LEER DOCUMENTO (GET /file/<uid>/<filename>)
# -------------------------------------------------------------
@app.get("/file/<uid>/<filename>")
async def obtener_documento(uid, filename):
    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_txt):
        return jsonify({"error": "Archivo no encontrado"}), 404

    # 1. Comprobar visibilidad leyendo el archivo .meta
    es_publico = False
    if os.path.exists(ruta_meta):
        async with aiofiles.open(ruta_meta, "r") as f:
            contenido_meta = await f.read()
            datos_meta = json.loads(contenido_meta)
            es_publico = datos_meta.get("public", False)

    # 2. Si es privado, exigir autenticación del propietario
    if not es_publico:
        if not verificar_token(uid, request.headers.get("Authorization")):
            return jsonify({"error": "Acceso denegado (archivo privado)"}), 401

    # 3. Leer y devolver el contenido
    async with aiofiles.open(ruta_txt, "r") as f:
        contenido = await f.read()

    return jsonify({"content": contenido}), 200


# -------------------------------------------------------------
# RUTA 4: BORRAR DOCUMENTO (DELETE /file/<uid>/<filename>)
# -------------------------------------------------------------
@app.delete("/file/<uid>/<filename>")
async def eliminar_documento(uid, filename):
    # 1. Verificar autenticación
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_txt):
        return jsonify({"error": "Archivo no encontrado"}), 404

    # 2. Borrar ambos archivos
    os.remove(ruta_txt)
    if os.path.exists(ruta_meta):
        os.remove(ruta_meta)

    return jsonify({"mensaje": "Archivo eliminado con éxito"}), 200


# -------------------------------------------------------------
# RUTA 5: CAMBIAR VISIBILIDAD (PATCH /file/<uid>/<filename>)
# -------------------------------------------------------------
@app.patch("/file/<uid>/<filename>")
async def cambiar_visibilidad(uid, filename):
    # 1. Verificar autenticación
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    # 2. Leer la petición
    datos = await request.get_json()
    if not datos or "public" not in datos:
        return jsonify({"error": "Falta el campo 'public' en el JSON"}), 400

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_meta):
        return jsonify({"error": "Archivo no encontrado"}), 404

    # 3. Actualizar el archivo .meta
    async with aiofiles.open(ruta_meta, "w") as f:
        await f.write(json.dumps({"public": datos["public"]}))

    return jsonify({"mensaje": "Visibilidad actualizada"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051)