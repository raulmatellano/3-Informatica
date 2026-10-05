import os
import json
import uuid
import aiofiles
from quart import Quart, request, jsonify

app = Quart(__name__)

SECRET_UUID = uuid.UUID("5624da4e-a64c-4943-b5d5-67ced4d90171")

DIR_FICHEROS = "almacenamiento/ficheros"
os.makedirs(DIR_FICHEROS, exist_ok=True)


def verificar_token(uid: str, auth_header: str) -> bool:
    if not auth_header:
        return False
    token_recibido = auth_header.replace("Bearer ", "").strip()
    token_esperado = str(uuid.uuid5(SECRET_UUID, str(uid)))
    return token_recibido == token_esperado


@app.get("/file/<uid>")
async def listar_documentos(uid):
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    if not os.path.exists(ruta_usuario):
        return jsonify({"ficheros": []}), 200

    archivos = os.listdir(ruta_usuario)
    documentos = [f for f in archivos if not f.endswith(".meta")]

    return jsonify({"ficheros": documentos}), 200


@app.put("/file/<uid>/<filename>")
async def crear_o_actualizar_documento(uid, filename):
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    if not datos or "content" not in datos:
        return jsonify({"error": "Falta el campo 'content' en el JSON"}), 400

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    os.makedirs(ruta_usuario, exist_ok=True)

    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"
    
    es_nuevo = not os.path.exists(ruta_txt)

    async with aiofiles.open(ruta_txt, "w") as f:
        await f.write(datos["content"])

    if es_nuevo:
        async with aiofiles.open(ruta_meta, "w") as f:
            await f.write(json.dumps({"public": False}))
            
    codigo_respuesta = 201 if es_nuevo else 200
    return jsonify({"mensaje": "Archivo guardado con éxito"}), codigo_respuesta


@app.get("/file/<uid>/<filename>")
async def obtener_documento(uid, filename):
    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_txt):
        return jsonify({"error": "Archivo no encontrado"}), 404

    es_publico = False
    if os.path.exists(ruta_meta):
        async with aiofiles.open(ruta_meta, "r") as f:
            contenido_meta = await f.read()
            datos_meta = json.loads(contenido_meta)
            es_publico = datos_meta.get("public", False)

    if not es_publico:
        if not verificar_token(uid, request.headers.get("Authorization")):
            return jsonify({"error": "Acceso denegado (archivo privado)"}), 401

    async with aiofiles.open(ruta_txt, "r") as f:
        contenido = await f.read()

    return jsonify({"content": contenido}), 200


@app.delete("/file/<uid>/<filename>")
async def eliminar_documento(uid, filename):
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_txt = f"{ruta_usuario}/{filename}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_txt):
        return jsonify({"error": "Archivo no encontrado"}), 404

    os.remove(ruta_txt)
    if os.path.exists(ruta_meta):
        os.remove(ruta_meta)

    return jsonify({"mensaje": "Archivo eliminado con éxito"}), 200


@app.patch("/file/<uid>/<filename>")
async def cambiar_visibilidad(uid, filename):
    if not verificar_token(uid, request.headers.get("Authorization")):
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    if not datos or "public" not in datos:
        return jsonify({"error": "Falta el campo 'public' en el JSON"}), 400

    ruta_usuario = f"{DIR_FICHEROS}/{uid}"
    ruta_meta = f"{ruta_usuario}/{filename}.meta"

    if not os.path.exists(ruta_meta):
        return jsonify({"error": "Archivo no encontrado"}), 404

    async with aiofiles.open(ruta_meta, "w") as f:
        await f.write(json.dumps({"public": datos["public"]}))

    return jsonify({"mensaje": "Visibilidad actualizada"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051)