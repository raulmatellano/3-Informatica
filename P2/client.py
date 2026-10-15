"""
Suite de pruebas de integración para la API del videoclub.
Valida endpoints de usuarios (user.py:5050) y películas/pedidos (api.py:5051).
"""
import requests

# URLs base de ambos microservicios
URL_USER = "http://localhost:5050"
URL_API = "http://localhost:5051"

token = ""
user_id = 0
pelicula_id = 0

# Helper para validar respuesta HTTP frente al código de estado esperado
def test(numero, descripcion, respuesta, codigo_esperado):
    if respuesta.status_code == codigo_esperado:
        print(f"[PASS] Prueba {numero}: {descripcion}")
    else:
        print(f"[FAIL] Prueba {numero}: {descripcion} (Esperaba {codigo_esperado}, recibí {respuesta.status_code})")
        print(f"       Respuesta: {respuesta.text}")

print("=========================================")
print("  INICIANDO PRUEBAS DEL VIDEOCLUB (P2)   ")
print("=========================================")

# ---------------------------------------------------------
# PRUEBAS DE USUARIOS (user.py)
# ---------------------------------------------------------

# 01: Registro correcto de usuario con saldo inicial
datos_registro = {"username": "alumno_uam", "password": "123", "pais": "España", "saldo": 50.0}
r = requests.put(f"{URL_USER}/user", json=datos_registro)
test("01", "Registro exitoso (PUT /user)", r, 201)

if r.status_code == 201:
    user_id = r.json().get("user_id")

# 02: Registro duplicado debe fallar con 409 Conflict
r = requests.put(f"{URL_USER}/user", json=datos_registro)
test("02", "Username duplicado (PUT /user)", r, 409)

# 03: Login con credenciales correctas devuelve 200 y token
datos_login = {"username": "alumno_uam", "password": "123"}
r = requests.post(f"{URL_USER}/user/login", json=datos_login)
test("03", "Login correcto (POST /user/login)", r, 200)

if r.status_code == 200:
    token = r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# 04: Login con contraseña incorrecta debe devolver 401 Unauthorized
datos_login_mal = {"username": "alumno_uam", "password": "mal"}
r = requests.post(f"{URL_USER}/user/login", json=datos_login_mal)
test("04", "Contraseña errónea (POST /user/login)", r, 401)

# 05: Recarga de saldo con token autenticado
r = requests.patch(f"{URL_USER}/user/alumno_uam/saldo", json={"cantidad": 20.5}, headers=headers)
test("05", "Actualizar saldo (PATCH /user/<u>/saldo)", r, 200)

# 18: Intento de borrado sin cabecera de autenticación debe fallar
r = requests.delete(f"{URL_USER}/user/alumno_uam")
test("18", "Borrar usuario sin token (DELETE /user/<u>)", r, 401)

# ---------------------------------------------------------
# PRUEBAS DE LA API PRINCIPAL (api.py)
# ---------------------------------------------------------

# 17: Creación de película sin token debe ser rechazada (401)
datos_peli = {"titulo": "Prueba", "director_id": 1, "anio": 2026, "precio": 10.0, "stock": 5}
r = requests.put(f"{URL_API}/pelicula", json=datos_peli)
test("17", "Crear película sin token (PUT /pelicula)", r, 401)

# 07: Creación autorizada de película asociada a un director
r = requests.put(f"{URL_API}/pelicula", json=datos_peli, headers=headers)
test("07", "Crear película (PUT /pelicula)", r, 201)
if r.status_code == 201:
    pelicula_id = r.json().get("pelicula_id")

# 09: Búsqueda y filtrado de películas por director
r = requests.get(f"{URL_API}/peliculas?director_id=1")
test("09", "Filtrar por director (GET /peliculas)", r, 200)

# 10: Añadir ítem al carrito (dispara trigger para decrementar stock)
r = requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1}, headers=headers)
test("10", "Añadir al carrito (POST /carrito/<uid>)", r, 201)

# 11: Pago del pedido con saldo suficiente (descuenta saldo y asigna fecha_pago)
r = requests.post(f"{URL_API}/carrito/{user_id}/pagar", headers=headers)
test("11", "Pagar carrito (POST /carrito/<uid>/pagar)", r, 200)

# 12: Simulación de saldo insuficiente al intentar pagar un nuevo pedido (debe fallar con 402)
requests.patch(f"{URL_USER}/user/alumno_uam/saldo", json={"cantidad": -70}, headers=headers)
requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1}, headers=headers)
r = requests.post(f"{URL_API}/carrito/{user_id}/pagar", headers=headers)
test("12", "Saldo insuficiente (POST /carrito/<uid>/pagar)", r, 402)

# 13: Emitir voto válido (0 a 10) para la película
r = requests.post(f"{URL_API}/pelicula/{pelicula_id}/voto", json={"puntuacion": 9}, headers=headers)
test("13", "Votar película (POST /pelicula/<id>/voto)", r, 201)

# 14: Voto con valor fuera de rango debe ser rechazado (400)
r = requests.post(f"{URL_API}/pelicula/{pelicula_id}/voto", json={"puntuacion": 15}, headers=headers)
test("14", "Voto fuera de rango (POST /pelicula/<id>/voto)", r, 400)

# 15: Consulta de la nota media calculada mediante stored procedure
r = requests.get(f"{URL_API}/pelicula/{pelicula_id}/puntuacion")
test("15", "Media de votos (GET /pelicula/<id>/puntuacion)", r, 200)

# 16: Consulta analítica de ventas agrupadas por año y país
r = requests.get(f"{URL_API}/ventas/2026/España")
test("16", "Ventas por año y país (GET /ventas/<anio>/<pais>)", r, 200)

# ---------------------------------------------------------
# LIMPIEZA DE DATOS DE PRUEBA
# ---------------------------------------------------------

# 08: Borrado de la película creada durante el test
r = requests.delete(f"{URL_API}/pelicula/{pelicula_id}", headers=headers)
test("08", "Borrar película (DELETE /pelicula/<id>)", r, 200)

# 06: Borrado del usuario de prueba
r = requests.delete(f"{URL_USER}/user/alumno_uam", headers=headers)
test("06", "Borrar usuario (DELETE /user/<u>)", r, 200)

print("=========================================")
print("          FIN DE LAS PRUEBAS             ")
print("=========================================")