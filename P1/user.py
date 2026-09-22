import os
import json
import uuid
import hashlib
from quart import Quart, request, jsonify

# Inicializamos la aplicacion Quart
app = Quart(__name__)

# Definimos las rutas donde vamos a guardar los datos de los usuarios y ficheros.
# El punto inicial './' significa "en el directorio actual"
ALMACENAMIENTO_USUARIOS = './almacenamiento/usuarios'
ALMACENAMIENTO_FICHEROS = './almacenamiento/ficheros'

# Leemos el SECRET_UUID desde las variables de entorno. 
# Si no existe, usamos uno por defecto para que la app no falle al arrancar.
# Convertimos el string a objeto UUID porque uuid.uuid5 lo va a necesitar asi.
SECRET_UUID = uuid.UUID(os.getenv('SECRET_UUID', '12345678-1234-5678-1234-567812345678'))

# Nos aseguramos de que las carpetas existan antes de empezar a guardar nada.
# exist_ok=True evita que de error si las carpetas ya existen.
os.makedirs(ALMACENAMIENTO_USUARIOS, exist_ok=True)
os.makedirs(ALMACENAMIENTO_FICHEROS, exist_ok=True)

# -------------------------------------------------------------
# Endpoint para registrar un usuario nuevo
# -------------------------------------------------------------
@app.route('/user', methods=['PUT'])
async def crear_usuario():
    # Obtenemos los datos JSON que envia el cliente en el cuerpo de la peticion
    datos = await request.get_json()
    
    # Comprobamos que nos han enviado datos y que contienen name y password
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
    
    # Guardamos los datos en variables para que sea mas facil leer el codigo
    name = datos['name']
    password = datos['password']
    
    # Comprobamos si ya existe el archivo JSON del usuario. Si existe, devolvemos error 409
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if os.path.exists(ruta_usuario):
        return jsonify({"error": "El usuario ya existe"}), 409
    
    # Generamos un UID aleatorio unico para el usuario (uuid4 genera IDs aleatorios)
    uid = str(uuid.uuid4())
    
    # Generamos el token usando uuid5. uuid5 genera siempre el mismo resultado 
    # si le pasamos el mismo SECRET_UUID y el mismo uid. Asi el microservicio de archivos
    # podra verificar el token sin tener que conectarse a este servicio de usuarios.
    token = str(uuid.uuid5(SECRET_UUID, uid))
    
    # Encriptamos la contraseña con SHA256 por seguridad. Nunca hay que guardar contraseñas en texto plano.
    contrasena_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Preparamos el diccionario con los datos a guardar
    usuario_datos = {
        "uid": uid,
        "token": token,
        "contrasena_hash": contrasena_hash
    }
    
    # Abrimos el fichero del usuario en modo escritura ('w') y guardamos el diccionario como JSON
    with open(ruta_usuario, 'w') as f:
        json.dump(usuario_datos, f)
        
    # Creamos la carpeta donde este usuario guardara sus ficheros
    os.makedirs(f"{ALMACENAMIENTO_FICHEROS}/{uid}", exist_ok=True)
    
    # Devolvemos el uid y token recien creados con codigo 201 (Created)
    return jsonify({"uid": uid, "token": token}), 201


# -------------------------------------------------------------
# Endpoint para iniciar sesion (login)
# -------------------------------------------------------------
@app.route('/user', methods=['POST'])
async def login():
    datos = await request.get_json()
    
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
        
    name = datos['name']
    password = datos['password']
    
    # Si el archivo JSON no existe, significa que el usuario no esta registrado
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if not os.path.exists(ruta_usuario):
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    # Leemos el archivo JSON del usuario para ver sus datos
    with open(ruta_usuario, 'r') as f:
        usuario_datos = json.load(f)
        
    # Calculamos el hash de la contraseña que ha introducido el usuario y lo comparamos
    # con el hash que guardamos cuando se registro
    hash_calculado = hashlib.sha256(password.encode()).hexdigest()
    if hash_calculado != usuario_datos['contrasena_hash']:
        return jsonify({"error": "Contraseña incorrecta"}), 401
        
    # Si coinciden, login correcto. Devolvemos su uid y token
    return jsonify({
        "uid": usuario_datos['uid'],
        "token": usuario_datos['token']
    }), 200


# -------------------------------------------------------------
# Endpoint para cambiar la contraseña de un usuario existente
# -------------------------------------------------------------
@app.route('/user', methods=['PATCH'])
async def modificar_contrasena():
    datos = await request.get_json()
    if not datos or 'name' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan campos"}), 400
        
    name = datos['name']
    nueva_password = datos['password']
    
    # Para cambiar la password necesitamos verificar que el usuario este logueado.
    # El token viene en la cabecera 'Authorization' con el formato 'Bearer <token>'
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"error": "Falta token"}), 401
        
    # Hacemos un split por el espacio y cogemos la segunda parte, que es el token real
    token_recibido = auth.split(" ")[1]
        
    ruta_usuario = f"{ALMACENAMIENTO_USUARIOS}/{name}.json"
    if not os.path.exists(ruta_usuario):
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    # Leemos los datos del usuario para saber su UID
    with open(ruta_usuario, 'r') as f:
        usuario_datos = json.load(f)
        
    uid = usuario_datos['uid']
    
    # Calculamos el token esperado para este UID igual que lo hicimos en el registro
    token_esperado = str(uuid.uuid5(SECRET_UUID, uid))
    
    # Comprobamos que el token recibido es correcto
    if token_recibido != token_esperado:
        return jsonify({"error": "Token invalido"}), 401
        
    # Actualizamos el hash con la nueva password y lo guardamos
    nuevo_hash = hashlib.sha256(nueva_password.encode()).hexdigest()
    usuario_datos['contrasena_hash'] = nuevo_hash
    
    with open(ruta_usuario, 'w') as f:
        json.dump(usuario_datos, f)
        
    return jsonify({"message": "Contraseña cambiada"}), 200


# Solo arrancamos la app si se ejecuta este fichero directamente (no si se importa)
if __name__ == '__main__':
    # Arrancamos en el puerto 5050 para que el cliente lo encuentre ahi
    app.run(host="0.0.0.0", port=5050)
