import requests

URL_USER = "http://localhost:5050"
URL_API = "http://localhost:5051"

token = ""
user_id = 0
pelicula_id = 0

# Comprueba el resultado de una peticion contra el codigo esperado
def test(num, desc, res, esperado):
    if res.status_code == esperado:
        print(f"OK - Prueba {num}: {desc}")
    else:
        print(f"FALLO - Prueba {num}: {desc} (Dio {res.status_code}, esperaba {esperado})")
        print(f"Info extra: {res.text}")

print("PRUEBAS VIDEOCLUB P2")

datos_registro = {"username": "alumno_uam", "password": "123", "pais": "España", "saldo": 50.0}

r = requests.put(f"{URL_USER}/user", json=datos_registro)
test("1", "Registro bien", r, 201)
if r.status_code == 201:
    user_id = r.json().get("user_id")

r = requests.put(f"{URL_USER}/user", json=datos_registro)
test("2", "Registro duplicado", r, 409)

datos_login = {"username": "alumno_uam", "password": "123"}
r = requests.post(f"{URL_USER}/user/login", json=datos_login)
test("3", "Login bien", r, 200)
if r.status_code == 200:
    token = r.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}

datos_login_mal = {"username": "alumno_uam", "password": "mal"}
r = requests.post(f"{URL_USER}/user/login", json=datos_login_mal)
test("4", "Login mal (contrasena mala)", r, 401)

r = requests.patch(f"{URL_USER}/user/alumno_uam/saldo", json={"cantidad": 20.5})
test("5", "Meter saldo sin token", r, 401)

r = requests.patch(f"{URL_USER}/user/alumno_uam/saldo", json={"cantidad": 20.5}, headers=headers)
test("6", "Meter saldo bien", r, 200)

r = requests.post(f"{URL_USER}/user/logout", headers=headers)
test("7", "Logout bien", r, 200)

r = requests.delete(f"{URL_USER}/user/alumno_uam")
test("8", "Borrar cuenta sin token", r, 401)

peli = {"titulo": "Prueba", "director_id": 1, "anio": 2026, "precio": 10.0, "stock": 5}
r = requests.put(f"{URL_API}/pelicula", json=peli)
test("9", "Crear peli sin token", r, 401)

r = requests.put(f"{URL_API}/pelicula", json=peli, headers=headers)
test("10", "Crear peli bien", r, 201)
if r.status_code == 201:
    pelicula_id = r.json().get("pelicula_id")

r = requests.get(f"{URL_API}/peliculas?director_id=1")
test("11", "Filtro director", r, 200)

r = requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1})
test("12", "Meter peli al carrito sin token", r, 401)

r = requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1}, headers=headers)
test("13", "Meter peli al carrito bien", r, 201)

r = requests.delete(f"{URL_API}/carrito/{user_id}/{pelicula_id}", headers=headers)
test("14", "Borrar peli del carrito", r, 200)

r = requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1}, headers=headers)
test("15", "Volver a meter peli al carrito", r, 201)

r = requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 15}, headers=headers)
test("16", "Meter al carrito sin stock suficiente", r, 500)

r = requests.post(f"{URL_API}/carrito/{user_id}/pagar", headers=headers)
test("17", "Pagar el carrito", r, 200)

requests.patch(f"{URL_USER}/user/alumno_uam/saldo", json={"cantidad": -60}, headers=headers)
requests.post(f"{URL_API}/carrito/{user_id}", json={"pelicula_id": pelicula_id, "cantidad": 1}, headers=headers)
r = requests.post(f"{URL_API}/carrito/{user_id}/pagar", headers=headers)
test("18", "Pagar sin dinero suficiente", r, 402)

r = requests.post(f"{URL_API}/pelicula/{pelicula_id}/voto", json={"puntuacion": 9})
test("19", "Votar sin token", r, 401)

r = requests.post(f"{URL_API}/pelicula/{pelicula_id}/voto", json={"puntuacion": 9}, headers=headers)
test("20", "Votar bien", r, 201)

r = requests.post(f"{URL_API}/pelicula/{pelicula_id}/voto", json={"puntuacion": 15}, headers=headers)
test("21", "Votar fuera de rango", r, 400)

r = requests.get(f"{URL_API}/pelicula/{pelicula_id}/puntuacion")
test("22", "Ver nota media", r, 200)

r = requests.get(f"{URL_API}/ventas/2026/España")
test("23", "Ver listado de ventas", r, 200)

r = requests.delete(f"{URL_API}/pelicula/{pelicula_id}", headers=headers)
test("24", "Borrar peli", r, 200)

r = requests.delete(f"{URL_USER}/user/alumno_uam", headers=headers)
test("25", "Borrar usuario", r, 200)

print("FIN PRUEBAS")
