import os
import json
import uuid
from quart import Quart, request, jsonify

# ==============================================================================
# EXPLICACIÓN BÁSICA:
# Este es el SERVICIO DE FICHEROS. Se encarga de guardar, borrar y listar los 
# documentos de texto de los usuarios. Solo permite acceso si el Token es correcto.
# ==============================================================================

app = Quart(__name__)

# La carpeta donde se guardan las carpetas de todos los usuarios
ALMACENAMIENTO_FICHEROS = './almacenamiento/ficheros'

# El mismo SECRET_UUID (la clave maestra) que usa user.py. 
# Gracias a que ambos servicios conocen esta clave, este servicio puede verificar 
# si un token es válido sin tener que comunicarse por red con el servicio de usuarios.
SECRET_UUID = uuid.UUID(os.getenv('SECRET_UUID', '12345678-1234-5678-1234-567812345678'))


# ==============================================================================
# ENDPOINT: LISTAR DOCUMENTOS (GET /file/<uid>)
# ==============================================================================
# <uid> en la ruta significa que la URL va a traer el UID del usuario (ej: /file/12345)
@app.route('/file/<uid>', methods=['GET'])
async def listar_documentos(uid):
    
    # 1. COMPROBAR AUTENTICACIÓN: Extraemos el token de las cabeceras (headers).
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    
    # auth es "Bearer el_token_aqui", lo partimos y cogemos la segunda parte
    token = auth.split(" ")[1]
    
    # 2. VERIFICAR TOKEN: Recreamos el token matemáticamente. Si coincide con el 
    # que nos enviaron, sabemos que el usuario es quien dice ser.
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    # 3. BUSCAR CARPETA: Comprobamos que el usuario tenga una carpeta creada
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    if not os.path.exists(ruta_dir):
        return jsonify({"error": "Directorio no encontrado"}), 404
    
    # 4. LISTAR ARCHIVOS: os.listdir lee todos los archivos de esa carpeta
    archivos = os.listdir(ruta_dir)
    documentos = []
    
    # En la carpeta guardamos .txt (el texto) y .meta (si es publico o privado).
    # Solo queremos devolver al usuario la lista de nombres sin el ".txt".
    for f in archivos:
        if f.endswith('.txt'):
            documentos.append(f.replace('.txt', ''))
            
    return jsonify({"ficheros": documentos}), 200


# ==============================================================================
# ENDPOINT: CREAR O REEMPLAZAR DOCUMENTO (PUT /file/<uid>/<filename>)
# ==============================================================================
@app.route('/file/<uid>/<filename>', methods=['PUT'])
async def crear_o_actualizar_documento(uid, filename):
    
    # Comprobamos la autenticación igual que antes (solo el propietario puede subir)
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    # Leemos el texto que el usuario quiere guardar (debe venir en un JSON con la clave 'content')
    datos = await request.get_json()
    if not datos or 'content' not in datos:
        return jsonify({"error": "Falta content"}), 400
    
    content = datos['content']
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    
    # Por seguridad, nos aseguramos de que su carpeta exista
    os.makedirs(ruta_dir, exist_ok=True)
    
    # Definimos la ruta de dos archivos: 
    # - El .txt guardará el contenido que ha escrito el usuario.
    # - El .meta (metadata) guardará si es público o privado.
    ruta_archivo = f"{ruta_dir}/{filename}.txt"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    # Guardamos en la variable 'es_nuevo' si el archivo NO existía previamente.
    es_nuevo = not os.path.exists(ruta_archivo)
    
    # Escribimos el contenido en el .txt ('w' sobrescribe si ya existía)
    with open(ruta_archivo, 'w') as f:
        f.write(content)
        
    # Si el archivo se acaba de crear por primera vez, creamos también su .meta 
    # estableciendo por defecto que es privado ("publico": False)
    if es_nuevo:
        with open(ruta_meta, 'w') as f:
            json.dump({"publico": False}, f)
            
    # Según la documentación REST, devolver 201 significa "Creado" y 200 significa "Actualizado OK"
    status_code = 201 if es_nuevo else 200
    return jsonify({"message": "Ok"}), status_code


# ==============================================================================
# ENDPOINT: LEER DOCUMENTO (GET /file/<uid>/<filename>)
# ==============================================================================
@app.route('/file/<uid>/<filename>', methods=['GET'])
async def obtener_documento(uid, filename):
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    ruta_archivo = f"{ruta_dir}/{filename}.txt"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    # Si el .txt no existe, devolvemos error 404
    if not os.path.exists(ruta_archivo):
        return jsonify({"error": "No existe"}), 404
        
    # 1. COMPROBAR VISIBILIDAD: Abrimos el archivo .meta para ver si es público o no
    es_publico = False
    if os.path.exists(ruta_meta):
        with open(ruta_meta, 'r') as f:
            meta = json.load(f)
            # get('publico', False) coge el valor de 'publico', y si no existe asume False
            es_publico = meta.get('publico', False)
            
    # 2. Si NO es público, exigimos que nos envíen el token del dueño para dejarle leerlo.
    if not es_publico:
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "No autorizado"}), 401
        token = auth.split(" ")[1]
        
        token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
        if token != token_esperado:
            # Token erróneo -> Prohibido el acceso a documentos de otros (Código 403)
            return jsonify({"error": "Prohibido"}), 403
            
    # Si es público, o si es privado pero pasaron la comprobación del dueño, leemos el fichero.
    with open(ruta_archivo, 'r') as f:
        content = f.read()
        
    return jsonify({"content": content}), 200


# ==============================================================================
# ENDPOINT: BORRAR DOCUMENTO (DELETE /file/<uid>/<filename>)
# ==============================================================================
@app.route('/file/<uid>/<filename>', methods=['DELETE'])
async def eliminar_documento(uid, filename):
    
    # La eliminación SIEMPRE requiere ser el propietario (comprobación de token)
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
        
    # Borramos el fichero de texto del disco duro usando os.remove()
    os.remove(ruta_archivo)
    
    # Y también borramos su archivo de visibilidad asociado si existe
    if os.path.exists(ruta_meta):
        os.remove(ruta_meta)
        
    return jsonify({"message": "Eliminado"}), 200


# ==============================================================================
# ENDPOINT: CAMBIAR VISIBILIDAD PÚBLICO/PRIVADO (PATCH /file/<uid>/<filename>)
# ==============================================================================
@app.route('/file/<uid>/<filename>', methods=['PATCH'])
async def cambiar_visibilidad(uid, filename):
    
    # Verificamos autenticación (solo el dueño puede decidir si es público o no)
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "No autorizado"}), 401
    token = auth.split(" ")[1]
    
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    if token != token_esperado:
        return jsonify({"error": "No autorizado"}), 401
        
    # Leemos la petición, esperamos algo como: {"public": true} o {"public": false}
    datos = await request.get_json()
    if not datos or 'public' not in datos:
        return jsonify({"error": "Falta public"}), 400
        
    ruta_dir = f"{ALMACENAMIENTO_FICHEROS}/{uid}"
    ruta_meta = f"{ruta_dir}/{filename}.meta"
    
    if not os.path.exists(ruta_meta):
        return jsonify({"error": "No existe"}), 404
        
    # Leemos el archivo JSON .meta actual
    with open(ruta_meta, 'r') as f:
        meta = json.load(f)
        
    # Actualizamos su diccionario con el nuevo valor enviado por el usuario
    meta['publico'] = datos['public']
    
    # Sobrescribimos el archivo con la nueva información
    with open(ruta_meta, 'w') as f:
        json.dump(meta, f)
        
    return jsonify({"message": "Visibilidad cambiada"}), 200


if __name__ == '__main__':
    # El servicio de ficheros escucha en el puerto 5051 para no chocar con el 5050 de usuarios
    app.run(host="0.0.0.0", port=5051)
