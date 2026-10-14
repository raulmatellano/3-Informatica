import requests 
import random   
import string   
import sys      


URL_USUARIO = "http://127.0.0.1:5050"
URL_FICHERO = "http://127.0.0.1:5051"

pruebas_superadas = 0
total_pruebas = 19

def ejecutar_prueba(nombre, condicion):
    global pruebas_superadas
    if condicion:
        print(f"[PASS] {nombre}") 
        pruebas_superadas += 1
    else:
        print(f"[FAIL] {nombre}") 

def ejecutar_prueba_con_codigo(nombre, respuesta, codigo_esperado):
    if respuesta.status_code != codigo_esperado:
        print(f"       -> ESPERADO: {codigo_esperado}, RECIBIDO: {respuesta.status_code}")
        try:
            print(f"       -> DETALLE: {respuesta.json()}")
        except:
            pass
    ejecutar_prueba(nombre, respuesta.status_code == codigo_esperado)

def run_tests():
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    username = f"alice_{suffix}"
    password = "password123"
    nueva_password = "newpassword456"
    
    uid = None
    token = None
    filename = "testdoc"
    

    r = requests.put(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("PUT /user - crear usuario alice", r, 201)
    if r.status_code == 201:
        data = r.json()
        uid = data.get("uid")
        token = data.get("token")
        
    r = requests.put(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("PUT /user - usuario duplicado", r, 409)
    
    r = requests.put(f"{URL_USUARIO}/user", json={"password": password})
    ejecutar_prueba_con_codigo("PUT /user - sin nombre", r, 400)
    
    r = requests.post(f"{URL_USUARIO}/user", json={"name": username, "password": password})
    ejecutar_prueba_con_codigo("POST /user - login correcto", r, 200)
    
    r = requests.post(f"{URL_USUARIO}/user", json={"name": username, "password": "wrong"})
    ejecutar_prueba_con_codigo("POST /user - contraseña incorrecta", r, 401)
    
    r = requests.post(f"{URL_USUARIO}/user", json={"name": "no_existe_nunca", "password": "pass"})
    ejecutar_prueba_con_codigo("POST /user - usuario no existe", r, 404)
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    headers_invalidos = {"Authorization": "Bearer badtoken"}
    
    r = requests.patch(f"{URL_USUARIO}/user", json={"password": nueva_password}, headers=headers)
    ejecutar_prueba_con_codigo("PATCH /user - cambiar contraseña", r, 200)
    
    r = requests.patch(f"{URL_USUARIO}/user", json={"password": password}, headers=headers_invalidos)
    ejecutar_prueba_con_codigo("PATCH /user - token invalido", r, 401)
    
    if not uid:
        print("UID no disponible porque falló la creación de usuario. Saltando tests de ficheros...")
        return
        

    r = requests.put(f"{URL_FICHERO}/file/{uid}/{filename}", json={"content": "hola mundo"}, headers=headers)
    ejecutar_prueba_con_codigo("PUT /file - subir documento privado", r, 201)
    
    r = requests.put(f"{URL_FICHERO}/file/{uid}/{filename}", json={"content": "hola mundo"})
    ejecutar_prueba_con_codigo("PUT /file - sin token", r, 401)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file - listar documentos", r, 200)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}")
    ejecutar_prueba_con_codigo("GET /file - listar sin token", r, 401)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc privado propietario", r, 200)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}")
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc privado sin token", r, 401)
    
    r = requests.patch(f"{URL_FICHERO}/file/{uid}/{filename}", json={"public": True}, headers=headers)
    ejecutar_prueba_con_codigo("PATCH /file - hacer publico", r, 200)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}")
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc publico sin token", r, 200)
    
    r = requests.delete(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("DELETE /file - eliminar documento", r, 200)
    
    r = requests.get(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("GET /file/<filename> - doc eliminado", r, 404)
    
    r = requests.delete(f"{URL_FICHERO}/file/{uid}/{filename}", headers=headers)
    ejecutar_prueba_con_codigo("DELETE /file - archivo no existe", r, 404)

    print(f"\nResultado: {pruebas_superadas}/{total_pruebas} pruebas superadas")
    
    if pruebas_superadas != total_pruebas:
        sys.exit(1)

if __name__ == "__main__":
    try:
        run_tests() 
    except requests.exceptions.ConnectionError:
        print("ERROR: No se pudo conectar con los servicios. Asegúrate de que user.py y file.py están ejecutándose.")
        sys.exit(1)