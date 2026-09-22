import os
import json
import uuid
from quart import Quart, request, jsonify

# Inicializamos la aplicacion Quart
app = Quart(__name__)

# Definimos la ruta de la carpeta donde se guardan todos los directorios de los usuarios
ALMACENAMIENTO_FICHEROS = './almacenamiento/ficheros'

# El mismo SECRET_UUID que usa user.py para que los dos generen exactamente los mismos tokens.
# Se coge de la variable de entorno que inyecta docker-compose.
SECRET_UUID = uuid.UUID(os.getenv('SECRET_UUID', '12345678-1234-5678-1234-567812345678'))


# -------------------------------------------------------------
# Endpoint para ver los documentos que tiene un usuario
# -------------------------------------------------------------
@app.route('/file/<uid>', methods=['GET'])
async def listar_documentos(uid):
    # Obtenemos el token de la peticion ('Bearer <token>')
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    # Calculamos como deberia ser el token real de este UID para compararlo.
    # Al usar el mismo SECRET_UUID y uid, tiene que dar exactamente el mismo hash que en user.py
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    # Buscamos la carpeta especifica de este usuario usando su uid
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    if not os.path.exists(ruta_dir):
        return jsonify({"error": "Directorio no encontrado"}), 404
    
    # os.listdir nos da todos los archivos de una carpeta (.txt y .meta)
    archivos = os.listdir(ruta_dir)
    documentos = []
    
    # Recorremos los archivos y metemos en la lista solo los nombres de los .txt (sin la extension)
    for f in archivos:
        if f.endswith('.txt'):
            documentos.append(f.replace('.txt', ''))
            
    return jsonify({"ficheros": documentos}), 200


# -------------------------------------------------------------
# Endpoint para subir un archivo nuevo o reemplazar uno que ya exista
# -------------------------------------------------------------
@app.route('/file/<uid>/<filename>', methods=['PUT'])
async def crear_o_actualizar_documento(uid, filename):
    # Verificamos autenticacion (solo el propietario puede subir archivos)
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    # Leemos el contenido que se quiere guardar
    datos = await request.get_json()
    if not datos or 'content' not in datos:
        return jsonify({"error": "Falta content"}), 400
    
    content = datos['content']
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    
    # Nos aseguramos de que el directorio exista (por si el usuario acaba de registrarse)
    os.makedirs(ruta_dir, exist_ok=True)
    
    # Un archivo para el texto y un archivo meta para saber si es publico o privado
    ruta_archivo = f"{ruta_dir}/{filename}.txt"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    # Guardamos en una variable si el archivo ya existia antes o es nuevo (para devolver 200 o 201)
    es_nuevo = not os.path.exists(ruta_archivo)
    
    # Escribimos el contenido de texto en el archivo
    with open(ruta_archivo, 'w') as f:
        f.write(content)
        
    # Si es nuevo, creamos tambien su fichero .meta diciendo que por defecto es privado (publico: false)
    if es_nuevo:
        with open(ruta_meta, 'w') as f:
            json.dump({"publico": False}, f)
            
    # Devolvemos 201 (Created) si se ha creado de cero, o 200 (OK) si solo se ha actualizado
    status_code = 201 if es_nuevo else 200
    return jsonify({"message": "Ok"}), status_code


# -------------------------------------------------------------
# Endpoint para leer un documento (descargarlo)
# -------------------------------------------------------------
@app.route('/file/<uid>/<filename>', methods=['GET'])
async def obtener_documento(uid, filename):
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    ruta_archivo = f"{ruta_dir}/{filename}.txt"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "No existe"}), 404
        
    # Primero leemos el fichero .meta para saber si cualquiera puede verlo
    es_publico = False
    if os.path.exists(ruta_meta):
        with open(ruta_meta, 'r') as f:
            meta = json.load(f)
            es_publico = meta.get('publico', False)
            
    # Si no es publico, tenemos que comprobar que el que hace la peticion es su dueño (token correcto)
    if not es_publico:
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "No autorizado"}), 401
        token = auth.split(" ")[1]
        
        token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
        if token != token_esperado:
            # Token erroneo -> Prohibido el acceso
            return jsonify({"error": "Prohibido"}), 403
            
    # Abrimos el fichero de texto, lo leemos entero y lo devolvemos
    with open(ruta_archivo, 'r') as f:
        content = f.read()
        
    return jsonify({"content": content}), 200


# -------------------------------------------------------------
# Endpoint para borrar un documento
# -------------------------------------------------------------
@app.route('/file/<uid>/<filename>', methods=['DELETE'])
async def eliminar_documento(uid, filename):
    # Verificamos autenticacion (solo el dueño puede borrar)
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    ruta_archivo = f"{ruta_dir}/{filename}.txt"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "No existe"}), 404
        
    # Borramos el fichero de texto
    os.remove(ruta_archivo)
    
    # Y si existe el meta (siempre deberia, pero por si acaso), lo borramos tambien
    if os.path.exists(ruta_meta):
        os.remove(ruta_meta)
        
    return jsonify({"message": "Eliminado"}), 200


# -------------------------------------------------------------
# Endpoint para cambiar si un archivo es publico o privado
# -------------------------------------------------------------
@app.route('/file/<uid>/<filename>', methods=['PATCH'])
async def cambiar_visibilidad(uid, filename):
    # Verificamos autenticacion (solo el dueño puede cambiar la visibilidad)
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    datos = await request.get_json()
    if not datos or 'public' not in datos:
        return jsonify({"error": "Falta public"}), 400
        
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    if not os.path.exists(ruta_meta):
        return jsonify({"error": "No existe"}), 404
        
    # Leemos el JSON actual
    with open(ruta_meta, 'r') as f:
        meta = json.load(f)
        
    # Cambiamos el valor de "publico" por lo que nos mandan en la peticion (True o False)
    meta['publico'] = datos['public']
    
    # Sobrescribimos el archivo con los nuevos datos
    with open(ruta_meta, 'w') as f:
        json.dump(meta, f)
        
    return jsonify({"message": "Visibilidad cambiada"}), 200


# Solo arrancamos la app si se ejecuta este fichero directamente (no si se importa)
if __name__ == '__main__':
    # Arrancamos en el puerto 5051 para el servicio de ficheros
    app.run(host="0.0.0.0", port=5051)
