import os
import json
import uuid
import hashlib
from quart import Quart, request, jsonify

# ==============================================================================
# EXPLICACIÓN DE LIBRERÍAS (¿Por qué importamos esto?):
# - os: Nos permite interactuar con el sistema operativo (crear carpetas, leer variables).
# - json: Nos permite convertir texto a formato JSON (y viceversa) para guardar/leer datos.
# - uuid: Genera identificadores únicos (como DNIs virtuales para los usuarios).
# - hashlib: Nos sirve para encriptar las contraseñas (hashing) por seguridad.
# - quart: Es el entorno que usamos para crear el servidor web.
#   - Quart: Crea la aplicación principal.
#   - request: Nos permite leer los datos que nos envía el cliente (ej. el postman).
#   - jsonify: Convierte nuestros diccionarios de Python a JSON para enviarlos de vuelta.
# ==============================================================================

# Inicializamos la aplicación Quart (nuestro servidor web para usuarios)
app = Quart(__name__)

# Definimos las rutas donde vamos a guardar los datos de los usuarios y ficheros.
# El punto inicial './' significa "en el directorio actual donde ejecutamos el código".
# El enunciado pedía guardar los datos en ficheros y directorios para la persistencia.
ALMACENAMIENTO_USUARIOS = './almacenamiento/usuarios'
ALMACENAMIENTO_FICHEROS = './almacenamiento/ficheros'

# Leemos el SECRET_UUID desde las variables de entorno (configurado en docker-compose).
# Esta es una "clave maestra" que usamos para generar los tokens de manera predecible.
# Si la variable de entorno no existe (por si lo ejecutamos sin Docker), usamos una por defecto.
# Convertimos el texto a un objeto UUID porque la función uuid5 lo necesita en ese formato.
SECRET_UUID = uuid.UUID(os.getenv('SECRET_UUID', '12345678-1234-5678-1234-567812345678'))

# Nos aseguramos de que las carpetas existan antes de empezar a guardar nada.
# exist_ok=True evita que el programa de error si las carpetas ya existen.
os.makedirs(ALMACENAMIENTO_USUARIOS, exist_ok=True)
os.makedirs(ALMACENAMIENTO_FICHEROS, exist_ok=True)


# ==============================================================================
# ENDPOINT 1: CREAR USUARIO (PUT /user)
# ==============================================================================
# @app.route define qué ruta web y qué método HTTP (PUT) activan esta función.
@app.route('/user', methods=['PUT'])
async def crear_usuario():
    # 'async' y 'await' se usan porque Quart es asíncrono. Esto significa que mientras 
    # el servidor espera a leer los datos (que puede tardar), puede atender a otras personas.
    
    # Obtenemos los datos JSON que envía el cliente en el cuerpo de la petición.
    datos = await request.get_json()
    
    # Comprobamos que el cliente nos haya enviado datos y que tengan 'name' y 'password'.
    # Si falta algo, devolvemos un error 400 (Bad Request).
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
    
    # Guardamos los datos en variables para que sea más fácil leer el código
    name = datos['name']
    password = datos['password']
    
    # Comprobamos si ya existe un archivo JSON para este usuario (significa que ya está registrado).
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if os.path.exists(ruta_usuario):
        return jsonify({"error": "El usuario ya existe"}), 409 # 409 = Conflicto
    
    # Generamos un UID aleatorio único para el usuario usando uuid4() del enunciado.
    uid = str(uuid.uuid4())
    
    # Generamos el TOKEN usando uuid5() como pide el enunciado. 
    # uuid5() genera siempre el MISMO token si le pasamos el MISMO SECRET_UUID y el uid.
    # Así, el servicio de ficheros (file.py) podrá verificar el token matemáticamente sin preguntarle a user.py.
    token = str(uuid.uuid5(SECRET_UUID, uid))
    
    # Encriptamos la contraseña con SHA-256 por seguridad (nunca se guardan en texto plano).
    # encode() pasa el texto a bytes, sha256() la encripta, y hexdigest() la convierte en letras y números.
    contrasena_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Preparamos el "diccionario" de Python con los datos que queremos guardar en el archivo.
    usuario_datos = {
        "uid": uid,
        "token": token,
        "contrasena_hash": contrasena_hash
    }
    
    # Abrimos el fichero del usuario en modo escritura ('w' = write) y guardamos el diccionario como JSON.
    with open(ruta_usuario, 'w') as f:
        json.dump(usuario_datos, f)
        
    # Creamos la carpeta donde este usuario guardará sus ficheros (usando su UID como nombre).
    os.makedirs(f"{ALMACENAMIENTO_FICHEROS}/{uid}", exist_ok=True)
    
    # El enunciado pide devolver el uid y token. El código 201 significa "Creado con éxito".
    return jsonify({"uid": uid, "token": token}), 201


# ==============================================================================
# ENDPOINT 2: INICIAR SESIÓN (POST /user)
# ==============================================================================
@app.route('/user', methods=['POST'])
async def login():
    datos = await request.get_json()
    
    # Validamos que vengan los datos obligatorios
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
        
    name = datos['name']
    password = datos['password']
    
    # Si el archivo JSON de este usuario NO existe, significa que no está registrado.
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if not os.path.exists(ruta_usuario):
        return jsonify({"error": "Usuario no encontrado"}), 404 # 404 = No encontrado
        
    # Abrimos el archivo JSON del usuario en modo lectura ('r' = read) para ver sus datos.
    with open(ruta_usuario, 'r') as f:
        usuario_datos = json.load(f)
        
    # Calculamos el hash de la contraseña que acaba de escribir el usuario, y lo comparamos
    # con el hash que habíamos guardado cuando se registró.
    hash_calculado = hashlib.sha256(password.encode()).hexdigest()
    if hash_calculado != usuario_datos['contrasena_hash']:
        return jsonify({"error": "Contraseña incorrecta"}), 401 # 401 = No autorizado
        
    # Si coinciden, el login es correcto. Devolvemos su uid y token como pide el enunciado.
    return jsonify({
        "uid": usuario_datos['uid'],
        "token": usuario_datos['token']
    }), 200 # 200 = OK


# ==============================================================================
# ENDPOINT 3: CAMBIAR CONTRASEÑA (PATCH /user)
# ==============================================================================
@app.route('/user', methods=['PATCH'])
async def modificar_contrasena():
    datos = await request.get_json()
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
        
    name = datos['name']
    nueva_password = datos['password'] # Esta es la nueva contraseña que quieren poner
    
    # Para cambiar la password necesitamos verificar que el usuario tenga permiso (esté logueado).
    # El enunciado dice que el token se pasa en la cabecera 'Authorization' con formato 'Bearer <token>'
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "Falta token"}), 401
        
    # El texto viene así: "Bearer m1t0k3n...". 
    # Usamos split(" ") para partirlo por el espacio y cogemos el [1] que es el token real.
    token_recibido = auth.split(" ")[1]
        
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if not os.path.exists(ruta_usuario):
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    # Leemos los datos del usuario para saber cuál es su UID
    with open(ruta_usuario, 'r') as f:
        usuario_datos = json.load(f)
        
    uid = usuario_datos['uid']
    
    # Calculamos cómo DEBERÍA ser el token de este usuario usando nuestra clave maestra y su UID.
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    
    # Comprobamos que el token recibido coincida con el que nosotros calculamos.
    if token_recibido != token_esperado:
        return jsonify({"error": "Token invalido"}), 401
        
    # Si todo es correcto, actualizamos el hash de la contraseña y lo guardamos en su fichero JSON.
    nuevo_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
    usuario_datos['contrasena_hash'] = nuevo_hash
    
    with open(ruta_usuario, 'w') as f:
        json.dump(usuario_datos, f)
        
    return jsonify({"message": "Contraseña cambiada"}), 200


# ==============================================================================
# ARRANQUE DEL SERVIDOR
# ==============================================================================
# Esto asegura que el servidor solo arranque si ejecutamos "python user.py" 
# directamente, y no si otro programa intenta importar este código.
if __name__ == '__main__':
    # Arrancamos en el puerto 5050 (0.0.0.0 significa que acepte conexiones desde cualquier IP, necesario para Docker)
    app.run(host="0.0.0.0", port=5050)
