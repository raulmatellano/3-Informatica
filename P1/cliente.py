import requests # Librería externa para hacer peticiones HTTP (GET, POST, PUT, DELETE)
import random   # Para generar números y cosas aleatorias
import string   # Para obtener las letras del abecedario
import sys      # Para funciones del sistema, como terminar el programa forzosamente con sys.exit(1)

# ==============================================================================
# EXPLICACIÓN:
# Este es el CLIENTE DE PRUEBAS. Finge ser un usuario normal (como un navegador
# o Postman) que se intenta conectar a nuestra API para ver si todo funciona.
# ==============================================================================

# Definimos dónde están nuestros dos servicios según docker-compose
URL_USUARIO = "http://127.0.0.1:5050"
URL_FICHERO = "http://127.0.0.1:5051"

# Contadores para saber cuántas pruebas hemos pasado
pruebas_superadas = 0
total_pruebas = 19

# Función auxiliar para imprimir por pantalla si una prueba pasa o falla
def ejecutar_prueba(nombre, condicion):
    global pruebas_superadas
    if condicion:
        print(f"[PASS] {nombre}") # [PASS] significa APROBADO
        pruebas_superadas += 1
    else:
        print(f"[FAIL] {nombre}") # [FAIL] significa FALLADO

# Función auxiliar que comprueba que el código HTTP devuelto sea el que esperamos (ej: 200, 401, 404)
def ejecutar_prueba_con_codigo(nombre, respuesta, codigo_esperado):
    # Si la respuesta no es la que esperábamos, imprimimos un mensaje de ayuda
    if respuesta.status_code != codigo_esperado:
        print(f"       -> ESPERADO: {codigo_esperado}, RECIBIDO: {respuesta.status_code}")
    # Llamamos a ejecutar_prueba pasándole True o False dependiendo de si los códigos coinciden
    ejecutar_prueba(nombre, respuesta.status_code == codigo_esperado)

# La función principal que ejecuta todos los tests secuencialmente
def run_tests():
    # Usamos un sufijo aleatorio de 4 letras/números para que el usuario sea distinto 
    # cada vez que ejecutamos el script. Así podemos probarlo varias veces sin tener 
    # que vaciar las carpetas a mano. (ej: alice_x8f9)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    username = f"alice_{suffix}"
    password = "password123"
    nueva_password = "newpassword456"
    
    uid = None
    token = None
    filename = "testdoc"
    
    # --------------------------------------------------------------------------
    # PRUEBAS DE USER.PY (Gestión de usuarios)
    # --------------------------------------------------------------------------

    # 01 PUT /user - crear usuario. Le mandamos un JSON con name y password. 
    # Esperamos 201 (Creado).
    r = requests.put(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("PUT /user - crear usuario alice", r, 201)
    if r.status_code == 201:
        # Si fue bien, guardamos el uid y token que nos devuelve para usarlos después
        data = r.json()
        uid = data.get("uid")
        token = data.get("token")
        
    # 02 PUT /user - Si intentamos crear el mismo usuario otra vez, debe dar 409 (Conflicto)
    r = requests.put(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("PUT /user - usuario duplicado", r, 409)
    
    # 03 PUT /user - Si no enviamos el nombre, debe dar 400 (Petición incorrecta)
    r = requests.put(f"{URL_USUARIO}/user", json={"password": password})
    ejecutar_prueba_con_codigo("PUT /user - sin nombre", r, 400)
    
    # 04 POST /user - Hacer login correctamente debe dar 200 (OK)
    r = requests.post(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("POST /user - login correcto", r, 200)
    
    # 05 POST /user - Poner la contraseña mal debe dar 401 (No autorizado)
    r = requests.post(f"{URL_USUARIO}/user", json={"name": username, "password": "wrong"})
    ejecutar_prueba_con_codigo("POST /user - contraseña incorrecta", r, 401)
    
    # 06 POST /user - Intentar entrar con alguien que no existe da 404 (No encontrado)
    r = requests.post(f"{URL_USUARIO}/user", json={"name": "no_existe_nunca", "password": "pass"})
    ejecutar_prueba_con_codigo("POST /user - usuario no existe", r, 404)
    
    # Preparamos las cabeceras (headers) que exigen los siguientes endpoints
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    headers_invalidos = {"Authorization": "Bearer badtoken"}
    
    # 07 PATCH /user - Cambiar la contraseña pasándole el Token bueno, debe dar 200
    r = requests.patch(f"{URL_USUARIO}/user", json={"name": username, "password": nueva_password}, headers=headers)
    ejecutar_prueba_con_codigo("PATCH /user - cambiar contraseña", r, 200)
    
    # 08 PATCH /user - Cambiarla con un token inventado debe fallar (401)
    r = requests.patch(f"{URL_USUARIO}/user", json={"name": username, "password": password}, headers=headers_invalidos)
    ejecutar_prueba_con_codigo("PATCH /user - token invalido", r, 401)
    
    if not uid:
        print("UID no disponible porque falló la creación de usuario. Saltando tests de ficheros...")
        return
        
    # --------------------------------------------------------------------------
    # PRUEBAS DE FILE.PY (Gestión de Ficheros)
    # --------------------------------------------------------------------------

    # 09 PUT /file - Subimos un documento "hola mundo" con nuestro token. Esperamos 201.
    r = requests.put(f"{URL_FICHERO}/file/{uid}/{filename}", json={"content": "hola mundo"}, headers=headers)
    ejecutar_prueba_con_codigo("PUT /file - subir documento privado", r, 201)
    
    # 10 PUT /file - Intentamos subir otro sin mandarle la cabecera del token. Esperamos 401.
    r = requests.put(f"{URL_FICHERO}/file/{uid}/{filename}", json={"content": "hola mundo"})
    ejecutar_prueba_con_codigo("PUT /file - sin token", r, 401)
    
    # 11 GET /file - Listar la carpeta usando nuestro token (200)
    r = requests.get(f"{URL_FICHERO}/file/{uid}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file - listar documentos", r, 200)
    
    # 12 GET /file - Listar sin token debe fallar (401)
    r = requests.get(f"{URL_FICHERO}/file/{uid}")
    ejecutar_prueba_con_codigo("GET /file - listar sin token", r, 401)
    
    # 13 GET /file/... - Intentamos leer nuestro propio documento privado pasándole el token (200)
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc privado propietario", r, 200)
    
    # 14 GET /file/... - Si lo intentamos leer pero sin el token, nos bloquea porque es privado (401)
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}")
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc privado sin token", r, 401)
    
    # 15 PATCH /file - Le decimos que queremos cambiarlo a público. Usamos el token. (200)
    r = requests.patch(f"{URL_FICHERO}/file/{uid}/{filename}", json={"public": True}, headers=headers)
    ejecutar_prueba_con_codigo("PATCH /file - hacer publico", r, 200)
    
    # 16 GET /file/... - Ahora que es público, intentamos leerlo SIN mandarle el token y debería dejarnos (200)
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}")
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc publico sin token", r, 200)
    
    # 17 DELETE /file - Borramos el archivo usando el token de propietario (200)
    r = requests.delete(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("DELETE /file - eliminar documento", r, 200)
    
    # 18 GET /file/... - Si intentamos leerlo otra vez, ya no está (404)
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc eliminado", r, 404)
    
    # 19 DELETE /file - Si intentamos borrar algo que ya no existe da error (404)
    r = requests.delete(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("DELETE /file - archivo no existe", r, 404)

    # Imprimimos el resumen de cómo ha ido todo
    print(f"\nResultado: {pruebas_superadas}/{total_pruebas} pruebas superadas")
    
    # Si alguna prueba falló, salimos con código 1 para indicar que hubo un error (útil para automatizaciones).
    if pruebas_superadas != total_pruebas:
        sys.exit(1)

# Este trozo de abajo es lo primero que se ejecuta al lanzar "python cliente.py"
if __name__ == "__main__":
    try:
        run_tests() # Llamamos a la función principal que hace todas las pruebas
    except requests.exceptions.ConnectionError:
        # Si da error de conexión (porque nos olvidamos de arrancar docker-compose), 
        # lo capturamos aquí para imprimir un mensaje amigable en lugar de un chorro de errores incomprensibles.
        print("ERROR: No se pudo conectar con los servicios. Asegúrate de que user.py y file.py están ejecutándose en Docker.")
        sys.exit(1)
