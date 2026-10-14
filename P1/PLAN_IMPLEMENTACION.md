# Práctica 1 — Microservicios. API REST en contenedor
*Sistemas Informáticos. Curso 2026/2027 — EPS Universidad Autónoma de Madrid*

---

## Descripción general

Se implementará un **servicio de almacenamiento de documentos de texto** compuesto por dos microservicios independientes:

- **Servicio de usuarios** (`user.py`): gestiona el registro, autenticación y modificación de contraseñas.
- **Servicio de ficheros** (`file.py`): gestiona el directorio de documentos por usuario (crear, leer, borrar, cambiar visibilidad).

Ambos microservicios se desarrollarán en **Python** usando **Quart** (framework ASGI), se comunicarán vía **API REST** con formato **JSON**, y se desplegarán en contenedores **Docker** coordinados por `docker-compose.yml`.

---

## Estructura de archivos del proyecto

```
P1/
├── user.py                  # Microservicio de usuarios  (puerto 5050)
├── file.py                  # Microservicio de ficheros  (puerto 5051)
├── cliente.py               # Cliente de pruebas automáticas
├── almacenamiento/          # Persistencia de datos (NO se entrega en el ZIP)
│   ├── usuarios/            # Un archivo JSON por usuario
│   └── ficheros/            # Un subdirectorio por UID de usuario
│       └── <uid>/
│           ├── <nombre_archivo>.txt   # Contenido del documento
│           └── <nombre_archivo>.meta  # Metadatos (visibilidad publica/privada)
├── Dockerfile.usuario       # Imagen Docker para user.py
├── Dockerfile.fichero       # Imagen Docker para file.py
├── docker-compose.yml       # Orquestación de contenedores
├── requirements.txt         # Dependencias Python (generado con pip freeze)
└── README.txt               # Instrucciones de despliegue y ejecución
```

> **Nota:** La carpeta `almacenamiento/` se crea automáticamente al ejecutar los servicios.
> No se entrega en el ZIP, pero los Dockerfiles la montan como volumen para persistir datos.

---

## Decisiones de diseño

| Aspecto | Decisión adoptada | Justificación |
|---|---|---|
| Framework | Quart (ASGI, async/await) | Indicado en el enunciado |
| Formato de comunicación | JSON | Indicado en el enunciado |
| Persistencia de usuarios | Un archivo `.json` por usuario en `almacenamiento/usuarios/` | Sencillo, legible, sin BD externa |
| Persistencia de ficheros | Subdirectorios por UID en `almacenamiento/ficheros/<uid>/` | Recomendado en el enunciado |
| Hash contraseñas | SHA-256 | Indicado en el enunciado |
| Generación de UID | `uuid.uuid4()` | Indicado en el enunciado |
| Generación de token | `uuid.uuid5(secret_uuid, uid_string)` — SHA-1 | Indicado en el enunciado |
| `secret_uuid` | Generado una sola vez y compartido por ambos servicios mediante variable de entorno `SECRET_UUID` | Permite que `file.py` valide tokens sin llamar a `user.py` |
| Puerto `user.py` | **5050** | Mencionado como ejemplo en el enunciado |
| Puerto `file.py` | **5051** | Convención natural siguiente |
| Metadatos de visibilidad | Archivo `<nombre>.meta` junto al documento con el campo `publico` | Sencillo, sin BD adicional |

---

## Resumen de endpoints (referencia rápida)

### Servicio `user.py` — Puerto 5050

| Método | Ruta | Body (JSON) | Headers | Respuesta éxito |
|---|---|---|---|---|
| `PUT` | `/user` | `{"name": "...", "password": "..."}` | — | `201` + `{"uid": "...", "token": "..."}` |
| `POST` | `/user` | `{"name": "...", "password": "..."}` | — | `200` + `{"uid": "...", "token": "..."}` |
| `PATCH` | `/user` | `{"name": "...", "password": "..."}` | `Authorization: Bearer <token>` | `200` |

### Servicio `file.py` — Puerto 5051

| Método | Ruta | Body (JSON) | Headers | Respuesta éxito |
|---|---|---|---|---|
| `GET` | `/file/<uid>` | — | `Authorization: Bearer <token>` | `200` + `{"ficheros": [...]}` |
| `PUT` | `/file/<uid>/<filename>` | `{"content": "..."}` | `Authorization: Bearer <token>` | `201` (nuevo) / `200` (actualizado) |
| `GET` | `/file/<uid>/<filename>` | — | `Authorization: Bearer <token>` (solo si privado) | `200` + `{"content": "..."}` |
| `DELETE` | `/file/<uid>/<filename>` | — | `Authorization: Bearer <token>` | `200` |
| `PATCH` | `/file/<uid>/<filename>` | `{"public": true/false}` | `Authorization: Bearer <token>` | `200` |

---

## PASO 0 — Preparación del entorno

**Objetivo:** tener el entorno de trabajo listo antes de empezar a programar.

### 0.1. Crear el entorno virtual Python

```bash
mkdir -p venv/si1p1
python3 -m venv venv/si1p1
source ./venv/si1p1/bin/activate
pip install quart requests
```

### 0.2. Crear la estructura de carpetas del proyecto

```bash
mkdir -p almacenamiento/usuarios
mkdir -p almacenamiento/ficheros
```

### 0.3. Archivos a crear/preparar en este paso

| Archivo | Acción | Descripción |
|---|---|---|
| `almacenamiento/usuarios/` | **CREAR directorio** | Donde se guardarán los datos de usuarios |
| `almacenamiento/ficheros/` | **CREAR directorio** | Donde se guardarán los documentos por UID |
| `requirements.txt` | **CREAR al final** | Generado con `pip freeze > requirements.txt` |
| `README.txt` | **CREAR (esqueleto)** | Instrucciones básicas de despliegue |

---

## PASO 1 — `file.py`: Microservicio de ficheros (sin tokens)

> **Semana 1 (primera parte)**
> Se implementa primero el servicio de ficheros **sin autenticación** para poder probar la lógica básica de almacenamiento antes de añadir seguridad.

- **Puerto:** 5051
- **Framework:** Quart
- **Persistencia:** `almacenamiento/ficheros/<uid>/`

### Qué contiene `file.py`

#### Inicialización de la aplicación Quart
- Crear la app con `app = Quart(__name__)`
- Leer `SECRET_UUID` desde variable de entorno (para fase 2)
- Punto de entrada: `app.run(host="0.0.0.0", port=5051)`

#### Función auxiliar: `verificar_token(uid, token)`
- **Fase 1 (ahora):** función que siempre devuelve `True` (sin comprobación real)
- **Fase 2 (Paso 3):** calcular `uuid.uuid5(secret_uuid, uid)` y comparar con el token recibido
- Retorna: `True` si válido, `False` si no

#### Función auxiliar: `extraer_token_cabecera(request)`
- **Fase 1 (ahora):** función que devuelve `None` (no se usa aún)
- **Fase 2 (Paso 3):** leer la cabecera `Authorization`, extraer la parte después de `Bearer `
- Retorna: el token como string, o `None` si no está presente o el formato es incorrecto

#### Endpoint 1: `listar_documentos(uid)` — `GET /file/<uid>`
- Leer el directorio `almacenamiento/ficheros/<uid>/`
- Devolver la lista de nombres de los archivos `.txt` (excluyendo los `.meta`)
- Si el directorio no existe → responder `404 Not Found`
- Respuesta JSON: `{"ficheros": ["doc1", "doc2", ...]}`
- Código HTTP éxito: `200 OK`

#### Endpoint 2: `crear_o_actualizar_documento(uid, filename)` — `PUT /file/<uid>/<filename>`
- Leer el cuerpo de la petición JSON: campo `content` con el texto del documento
- Si falta el campo `content` → `400 Bad Request`
- Crear el directorio `almacenamiento/ficheros/<uid>/` si no existe
- Escribir el contenido en `almacenamiento/ficheros/<uid>/<filename>.txt`
- Si el archivo es **nuevo**: crear también `almacenamiento/ficheros/<uid>/<filename>.meta` con `{"publico": false}`
- Si el archivo **ya existe**: reemplazar solo el contenido `.txt`, mantener el `.meta` intacto
- Respuesta: `201 Created` si es nuevo, `200 OK` si se actualiza

#### Endpoint 3: `obtener_documento(uid, filename)` — `GET /file/<uid>/<filename>`
- Leer `almacenamiento/ficheros/<uid>/<filename>.txt`
- Leer metadatos `almacenamiento/ficheros/<uid>/<filename>.meta`
- **Fase 1 (ahora):** devolver siempre el contenido si existe
- **Fase 2 (Paso 3):** comprobar visibilidad y token (ver Paso 3)
- Si no existe el archivo → `404 Not Found`
- Respuesta JSON: `{"content": "texto del documento"}`
- Código HTTP éxito: `200 OK`

#### Endpoint 4: `eliminar_documento(uid, filename)` — `DELETE /file/<uid>/<filename>`
- Eliminar `almacenamiento/ficheros/<uid>/<filename>.txt`
- Eliminar también `almacenamiento/ficheros/<uid>/<filename>.meta`
- Si no existe alguno de los dos → `404 Not Found`
- Respuesta: `200 OK`

#### Endpoint 5: `cambiar_visibilidad(uid, filename)` — `PATCH /file/<uid>/<filename>`
- Leer el cuerpo JSON: campo `public` (`true` o `false`)
- Si falta el campo `public` → `400 Bad Request`
- Leer el archivo `almacenamiento/ficheros/<uid>/<filename>.meta`
- Si no existe → `404 Not Found`
- Actualizar el campo `publico` en el `.meta` con el valor recibido
- Respuesta: `200 OK`

---

## PASO 2 — `user.py`: Microservicio de usuarios

> **Semana 1 (segunda parte)**
> Se implementa el servicio de usuarios completo con registro, login y cambio de contraseña.

- **Puerto:** 5050
- **Framework:** Quart
- **Persistencia:** Un archivo `almacenamiento/usuarios/<name>.json` por usuario

### Formato del archivo de usuario (`almacenamiento/usuarios/<name>.json`)

```json
{
  "uid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "token": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  "contrasena_hash": "sha256hexstring..."
}
```

### Qué contiene `user.py`

#### Inicialización de la aplicación Quart
- Crear la app con `app = Quart(__name__)`
- Leer o generar `SECRET_UUID` desde variable de entorno
- Crear el directorio `almacenamiento/usuarios/` si no existe al arrancar
- Punto de entrada: `app.run(host="0.0.0.0", port=5050)`

#### Función auxiliar: `calcular_hash_contrasena(password)`
- Calcular `hashlib.sha256(password.encode()).hexdigest()`
- Retorna: el hash como string hexadecimal

#### Función auxiliar: `calcular_token(uid)`
- Calcular `str(uuid.uuid5(secret_uuid, uid))`
- Retorna: el token como string

#### Función auxiliar: `leer_usuario(name)`
- Leer y parsear `almacenamiento/usuarios/<name>.json`
- Retorna: el diccionario con los datos del usuario, o `None` si no existe

#### Función auxiliar: `guardar_usuario(name, datos)`
- Serializar y escribir el diccionario `datos` en `almacenamiento/usuarios/<name>.json`

#### Endpoint 1: `crear_usuario()` — `PUT /user`
- Leer cuerpo JSON: campos `name` y `password`
- Si faltan `name` o `password` → `400 Bad Request`
- Si ya existe `almacenamiento/usuarios/<name>.json` → `409 Conflict`
- Generar `uid = str(uuid.uuid4())`
- Calcular `token = calcular_token(uid)`
- Calcular `contrasena_hash = calcular_hash_contrasena(password)`
- Guardar en `almacenamiento/usuarios/<name>.json`
- Crear el directorio `almacenamiento/ficheros/<uid>/` para que el usuario ya tenga su carpeta lista
- Respuesta JSON: `{"uid": "...", "token": "..."}`
- Código HTTP éxito: `201 Created`

#### Endpoint 2: `login()` — `POST /user`
- Leer cuerpo JSON: campos `name` y `password`
- Si faltan campos → `400 Bad Request`
- Leer el archivo del usuario con `leer_usuario(name)`
- Si no existe → `404 Not Found`
- Calcular hash de la contraseña recibida y comparar con `contrasena_hash` almacenado
- Si no coinciden → `401 Unauthorized`
- Respuesta JSON: `{"uid": "...", "token": "..."}`
- Código HTTP éxito: `200 OK`

#### Endpoint 3: `modificar_contrasena()` — `PATCH /user`
- Leer cuerpo JSON: campos `name` y `password` (nueva contraseña)
- Si faltan campos → `400 Bad Request`
- Leer la cabecera `Authorization: Bearer <token>`
- Si no hay cabecera → `401 Unauthorized`
- Leer el archivo del usuario con `leer_usuario(name)`
- Si no existe → `404 Not Found`
- Verificar que el token recibido coincide con `calcular_token(uid)` del usuario
- Si no coincide → `401 Unauthorized`
- Calcular nuevo hash y actualizar `contrasena_hash` en el archivo JSON del usuario con `guardar_usuario()`
- Respuesta: `200 OK`

---

## PASO 3 — Integrar autenticación en `file.py`

> **Semana 2**
> Se activa la verificación de tokens en el servicio de ficheros, usando la misma lógica que `user.py`.

### Cambios a realizar en `file.py`

#### Activar `verificar_token(uid, token)` (ya existe como esqueleto del Paso 1)
- Leer `SECRET_UUID` desde variable de entorno al arrancar la app
- Implementar: calcular `str(uuid.uuid5(secret_uuid, uid))` y comparar con el `token` recibido
- Retorna: `True` si coinciden, `False` si no

#### Activar `extraer_token_cabecera(request)` (ya existe como esqueleto del Paso 1)
- Implementar: leer `request.headers.get("Authorization")`
- Si no existe → retornar `None`
- Si existe pero no empieza por `Bearer ` → retornar `None`
- Extraer la parte después de `Bearer ` y retornarla como string

#### Añadir verificación de token a los endpoints protegidos

**`GET /file/<uid>` — `listar_documentos`:**
- Extraer token con `extraer_token_cabecera(request)`
- Si no hay token → `401 Unauthorized`
- Verificar token con `verificar_token(uid, token)`
- Si no es válido → `401 Unauthorized`
- Si es válido → continuar con la lógica existente

**`PUT /file/<uid>/<filename>` — `crear_o_actualizar_documento`:**
- Misma verificación de token que en `listar_documentos`
- Si no hay token o no es válido → `401 Unauthorized`

**`DELETE /file/<uid>/<filename>` — `eliminar_documento`:**
- Misma verificación de token
- Si no hay token o no es válido → `401 Unauthorized`

**`PATCH /file/<uid>/<filename>` — `cambiar_visibilidad`:**
- Misma verificación de token
- Si no hay token o no es válido → `401 Unauthorized`

**`GET /file/<uid>/<filename>` — `obtener_documento` (lógica especial):**
- Leer el archivo `.meta` para saber si el documento es público o privado
- Si el documento **es público** → devolver el contenido **sin requerir token**
- Si el documento **es privado**:
  - Extraer token con `extraer_token_cabecera(request)`
  - Si no hay token → `401 Unauthorized`
  - Verificar token con `verificar_token(uid, token)`
  - Si no es válido (no es el propietario) → `403 Forbidden`
  - Si es válido → devolver el contenido

---

## PASO 4 — `cliente.py`: Cliente de pruebas automáticas

> **Semana 3**
> Se implementa el cliente que prueba **todos los endpoints** de ambos servicios, incluyendo casos de error.

- **Herramienta:** librería `requests`
- **Modo:** no interactivo, cada prueba imprime `[PASS]` o `[FAIL]` con descripción

### URL base de cada servicio

```python
URL_USUARIO = "http://127.0.0.1:5050"
URL_FICHERO = "http://127.0.0.1:5051"
```

### Estructura del cliente

#### Función auxiliar: `ejecutar_prueba(nombre, condicion)`
- Imprime `[PASS] <nombre>` si `condicion` es `True`
- Imprime `[FAIL] <nombre>` si `condicion` es `False`

#### Función auxiliar: `ejecutar_prueba_con_codigo(nombre, respuesta, codigo_esperado)`
- Compara el código HTTP de la respuesta con el esperado
- Imprime resultado con `ejecutar_prueba()`

### Pruebas a implementar en orden

Las pruebas deben ejecutarse en este orden (cada una puede depender de la anterior):

| # | Nombre de la prueba | Endpoint | Caso | Código esperado |
|---|---|---|---|---|
| 01 | `PUT /user - crear usuario alice` | `PUT /user` | Registro exitoso | `201` |
| 02 | `PUT /user - usuario duplicado` | `PUT /user` | Usuario ya existe | `409` |
| 03 | `PUT /user - sin nombre` | `PUT /user` | Faltan campos | `400` |
| 04 | `POST /user - login correcto` | `POST /user` | Login exitoso | `200` |
| 05 | `POST /user - contraseña incorrecta` | `POST /user` | Contraseña errónea | `401` |
| 06 | `POST /user - usuario no existe` | `POST /user` | Usuario inexistente | `404` |
| 07 | `PATCH /user - cambiar contraseña` | `PATCH /user` | Cambio exitoso | `200` |
| 08 | `PATCH /user - token invalido` | `PATCH /user` | Token incorrecto | `401` |
| 09 | `PUT /file - subir documento privado` | `PUT /file/<uid>/<filename>` | Subida exitosa | `201` |
| 10 | `PUT /file - sin token` | `PUT /file/<uid>/<filename>` | Sin autenticación | `401` |
| 11 | `GET /file - listar documentos` | `GET /file/<uid>` | Listado exitoso | `200` |
| 12 | `GET /file - listar sin token` | `GET /file/<uid>` | Sin autenticación | `401` |
| 13 | `GET /file/<filename> - doc privado propietario` | `GET /file/<uid>/<filename>` | Acceso propio doc privado | `200` |
| 14 | `GET /file/<filename> - doc privado sin token` | `GET /file/<uid>/<filename>` | Acceso sin token a privado | `401` |
| 15 | `PATCH /file - hacer publico` | `PATCH /file/<uid>/<filename>` | Cambio visibilidad exitoso | `200` |
| 16 | `GET /file/<filename> - doc publico sin token` | `GET /file/<uid>/<filename>` | Acceso a doc público anónimo | `200` |
| 17 | `DELETE /file - eliminar documento` | `DELETE /file/<uid>/<filename>` | Eliminación exitosa | `200` |
| 18 | `GET /file/<filename> - doc eliminado` | `GET /file/<uid>/<filename>` | Doc ya no existe | `404` |
| 19 | `DELETE /file - archivo no existe` | `DELETE /file/<uid>/<filename>` | Eliminar inexistente | `404` |

### Formato de salida esperado al ejecutar el cliente

```
[PASS] PUT /user - crear usuario alice
[PASS] PUT /user - usuario duplicado
[PASS] PUT /user - sin nombre
[PASS] POST /user - login correcto
...
Resultado: 19/19 pruebas superadas
```

---

## PASO 5 — Docker: Dockerfiles y docker-compose

> **Semana 3 (parte final)**
> Se contenedorizan los dos microservicios para poder desplegarlos con Docker.

> **IMPORTANTE:** Los dos servicios necesitan **compartir el mismo `SECRET_UUID`**.
> Este valor se genera una sola vez y se pasa a ambos contenedores como variable de entorno en `docker-compose.yml`.

### Qué contiene `Dockerfile.usuario`

- Imagen base: `python:3.11-slim`
- Directorio de trabajo: `/app`
- Copiar `requirements.txt` e instalar dependencias con `pip install`
- Copiar `user.py`
- Exponer puerto `5050`
- Comando de arranque: ejecutar `user.py` con Quart escuchando en `0.0.0.0:5050`

### Qué contiene `Dockerfile.fichero`

- Imagen base: `python:3.11-slim`
- Directorio de trabajo: `/app`
- Copiar `requirements.txt` e instalar dependencias con `pip install`
- Copiar `file.py`
- Exponer puerto `5051`
- Comando de arranque: ejecutar `file.py` con Quart escuchando en `0.0.0.0:5051`

### Qué contiene `docker-compose.yml`

Debe definir **dos servicios**:

**Servicio `servicio-usuario`:**
- Construir desde `Dockerfile.usuario`
- Mapear puerto `5050:5050`
- Montar volumen: `./almacenamiento` → `/app/almacenamiento` (para persistir datos)
- Variable de entorno: `SECRET_UUID` (leída del entorno del host o de un `.env`)

**Servicio `servicio-fichero`:**
- Construir desde `Dockerfile.fichero`
- Mapear puerto `5051:5051`
- Montar volumen: `./almacenamiento` → `/app/almacenamiento` (mismo volumen compartido)
- Variable de entorno: `SECRET_UUID` (el mismo valor que para el servicio de usuario)

### Cómo gestionar el `SECRET_UUID`

- Generar una vez con: `python3 -c "import uuid; print(uuid.uuid4())"`
- Guardarlo en un archivo `.env` en la raíz del proyecto (excluido del ZIP de entrega):
  ```
  SECRET_UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  ```
- `docker-compose` lo lee automáticamente si existe el archivo `.env`

---

## PASO 6 — Preparar la entrega

> **Final de Semana 3**

### Archivos que se incluyen en `P1.zip`

| Archivo | Descripción |
|---|---|
| `user.py` | Microservicio de usuarios |
| `file.py` | Microservicio de ficheros |
| `cliente.py` | Cliente de pruebas automáticas |
| `Dockerfile.usuario` | Imagen Docker para user.py |
| `Dockerfile.fichero` | Imagen Docker para file.py |
| `docker-compose.yml` | Orquestación de ambos servicios |
| `requirements.txt` | Dependencias Python |
| `README.txt` | Instrucciones de despliegue y ejecución |

### Archivos que **NO** se incluyen en el ZIP

| Archivo/Carpeta | Motivo |
|---|---|
| `venv/` | Entorno virtual Python |
| `almacenamiento/` | Datos generados en ejecución |
| `__pycache__/`, `*.pyc` | Bytecodes de Python |
| `.DS_Store`, `Thumbs.db` | Metadatos del sistema operativo |
| `.env` | Contiene el `SECRET_UUID`, no debe compartirse |

### Generar `requirements.txt`

```bash
source ./venv/si1p1/bin/activate
pip freeze > requirements.txt
```

### Contenido mínimo de `README.txt`

- Nombre, grupo y equipo del alumno
- Versión de Python y dependencias necesarias
- Instrucciones para ejecutar **sin Docker** (con entorno virtual):
  ```bash
  source ./venv/si1p1/bin/activate
  export SECRET_UUID="<el-uuid-generado>"
  python user.py   # en una terminal
  python file.py   # en otra terminal
  python cliente.py
  ```
- Instrucciones para ejecutar **con Docker**:
  ```bash
  echo "SECRET_UUID=<el-uuid-generado>" > .env
  docker-compose up --build
  python cliente.py
  ```
- Descripción de los puertos usados: `user.py` → 5050 / `file.py` → 5051

---

## Rúbrica y puntuación

| Concepto | Puntuación máxima |
|---|---|
| Servicio `user.py` | 3 puntos |
| Servicio `file.py` | 3 puntos |
| Cliente de pruebas `cliente.py` | 2 puntos |
| Gestión de Docker (`Dockerfile` + `docker-compose`) | 1 punto |
| Memoria (autores, grupo y equipo en primera página) | 1 punto |
| **TOTAL** | **10 puntos** |

> **Penalización:** 1 punto por día natural (o fracción) de retraso en la entrega.

---

## Planificación recomendada

| Semana | Tarea |
|---|---|
| **Semana 1** | Paso 0 (entorno) + Paso 1 (`file.py` sin tokens) + Paso 2 (`user.py` completo) |
| **Semana 2** | Paso 3 (integrar tokens en `file.py`) |
| **Semana 3** | Paso 4 (`cliente.py`) + Paso 5 (Docker) + Paso 6 (entrega) |
