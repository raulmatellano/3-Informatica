# Práctica 2 — Videoclub. Microservicios + SQLAlchemy Async + PostgreSQL
*Sistemas Informáticos. Curso 2026/2027 — EPS Universidad Autónoma de Madrid*

---

## Descripción general

Videoclub distribuido con **dos microservicios independientes** sobre la misma BD PostgreSQL:

- **`user.py`** (puerto 5050): gestión de usuarios (registro, login, logout, saldo).
- **`api.py`** (puerto 5051): catálogo de películas, carrito, pedidos, votos.

Stack: **Quart** (ASGI async) + **SQLAlchemy Core async** (`asyncpg`) + **PostgreSQL** (contenedor).  
Auth: token cifrado en cabecera `Authorization: Bearer <token>`, **stateless** (no se guarda en BD).

---

## Estructura de carpetas

```
P2/
├── user.py                  # Microservicio usuarios  (puerto 5050)
├── api.py                   # Microservicio principal (puerto 5051)
├── client.py                # Cliente de pruebas automáticas
├── optimizacion.sql         # Script SQL con EXPLAIN y mejoras de índices
├── db_init.sql              # DDL: tablas, triggers, stored procedures
├── Dockerfile               # Imagen compartida (o dos separados)
├── docker-compose.yml       # BD + user + api
├── requirements.txt
└── README.txt
```

---

## Ejercicio 1 — Diseño de la Base de Datos

### Modelo E-R (entidades clave)

| Entidad | Atributos principales |
|---|---|
| `usuarios` | `id SERIAL PK`, `username UNIQUE`, `password_hash`, `pais`, `saldo NUMERIC` |
| `peliculas` | `id SERIAL PK`, `titulo`, `director`, `anio`, `precio NUMERIC`, `stock INT` |
| `pedidos` | `id SERIAL PK`, `usuario_id FK`, `fecha_pago TIMESTAMP NULL`, `total NUMERIC` |
| `pedido_peliculas` | `pedido_id FK`, `pelicula_id FK`, PK compuesta, `cantidad INT`, `precio_unitario NUMERIC` |
| `votos` | `usuario_id FK`, `pelicula_id FK`, PK compuesta, `puntuacion INT CHECK(0..10)` |

### Decisiones de diseño

| Aspecto | Decisión | Justificación |
|---|---|---|
| ORM vs Core | SQLAlchemy **Core** con `text()` en `api.py` | Obligatorio en enunciado |
| ORM para usuarios | SQLAlchemy **ORM async** en `user.py` | Permitido en enunciado |
| Carrito | Pedido con `fecha_pago IS NULL` = carrito abierto | Sin tabla extra |
| Token auth | `HMAC-SHA256(secret_key, username)` en Base64 | Stateless, verificable sin BD |
| Precio snapshot | `precio_unitario` en `pedido_peliculas` | Precio al momento de compra, inmutable |

---

## Ejercicio 2 — Triggers y Stored Procedures (`db_init.sql`)

### Trigger 1: `trg_actualizar_saldo_tras_pago`
- **Evento:** `AFTER UPDATE OF fecha_pago ON pedidos`
- **Condición:** `OLD.fecha_pago IS NULL AND NEW.fecha_pago IS NOT NULL`
- **Acción:** descuenta `total` del `saldo` del usuario propietario del pedido.

### Trigger 2: `trg_calcular_total_pedido`
- **Evento:** `AFTER INSERT ON pedido_peliculas`
- **Acción:** recalcula y actualiza `pedidos.total` sumando `(cantidad * precio_unitario)`.

### Stored Procedure: `sp_pagar_carrito(p_pedido_id INT)`
- Verifica que el pedido existe y no está pagado.
- Verifica que el saldo del usuario >= `total`.
- Actualiza `fecha_pago = NOW()` (dispara el trigger de saldo).
- Retorna el nuevo saldo restante.

---

## Ejercicio 3 — API de Usuarios (`user.py`, puerto 5050)

Usa **SQLAlchemy ORM async**.

| Método | Ruta | Body | Auth | Respuesta |
|---|---|---|---|---|
| `PUT` | `/user` | `{username, password, pais, saldo?}` | — | `201 {user_id, token}` |
| `DELETE` | `/user/<username>` | — | Bearer | `200` |
| `POST` | `/user/login` | `{username, password}` | — | `200 {user_id, token}` |
| `POST` | `/user/logout` | — | Bearer | `200` |
| `PATCH` | `/user/<username>/saldo` | `{cantidad}` | Bearer | `200 {saldo}` |

### Lógica de token (stateless)
```python
import hmac, hashlib, base64
token = base64.b64encode(
    hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).digest()
).decode()
```

---

## Ejercicio 4 — API Principal (`api.py`, puerto 5051)

Usa **SQLAlchemy Core async** con `text()` + `execute()` (prepared statements).
**Cada consulta = un solo `execute()`.**

### 4.1 Gestión de películas

| Método | Ruta | Body | Auth | Respuesta |
|---|---|---|---|---|
| `PUT` | `/pelicula` | `{titulo, director, anio, precio, stock}` | Bearer | `201 {pelicula_id}` |
| `DELETE` | `/pelicula/<id>` | — | Bearer | `200` |
| `GET` | `/peliculas` | Query params: `?director=`, `?anio=`, `?titulo=` | — | `200 [{pelicula}]` |

### 4.2 Carrito y pedidos

| Método | Ruta | Body | Auth | Respuesta |
|---|---|---|---|---|
| `POST` | `/carrito/<user_id>` | `{pelicula_id, cantidad}` | Bearer | `201` |
| `POST` | `/carrito/<user_id>/pagar` | — | Bearer | `200 {fecha_pago, total}` |
| `GET` | `/pedidos/<user_id>` | — | Bearer | `200 [{pedido}]` |

### 4.3 Votos

| Método | Ruta | Body | Auth | Respuesta |
|---|---|---|---|---|
| `POST` | `/pelicula/<id>/voto` | `{puntuacion}` | Bearer | `201` |
| `GET` | `/pelicula/<id>/puntuacion` | — | — | `200 {media}` |

### 4.4 Endpoint de ventas (para optimización)

| Método | Ruta | Auth | Respuesta |
|---|---|---|---|
| `GET` | `/ventas/<anio>/<pais>` | — | `200 [{venta}]` |

**Query base (un único `execute()`):**
```sql
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario,
       ped.fecha_pago
FROM pedidos ped
JOIN usuarios u ON ped.usuario_id = u.id
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id
JOIN peliculas p ON pp.pelicula_id = p.id
WHERE EXTRACT(YEAR FROM ped.fecha_pago) = :anio
  AND u.pais = :pais
  AND ped.fecha_pago IS NOT NULL;
```

---

## Ejercicio 5 — Cliente de pruebas (`client.py`)

Librería: `requests` (sync). Formato: `[PASS]`/`[FAIL]` por prueba.

### Pruebas mínimas a cubrir

| # | Endpoint | Caso | Código esperado |
|---|---|---|---|
| 01 | `PUT /user` | Registro exitoso | `201` |
| 02 | `PUT /user` | Username duplicado | `409` |
| 03 | `POST /user/login` | Login correcto | `200` |
| 04 | `POST /user/login` | Contraseña errónea | `401` |
| 05 | `PATCH /user/<u>/saldo` | Actualizar saldo | `200` |
| 06 | `DELETE /user/<u>` | Borrar usuario | `200` |
| 07 | `PUT /pelicula` | Crear película | `201` |
| 08 | `DELETE /pelicula/<id>` | Borrar película | `200` |
| 09 | `GET /peliculas?director=X` | Filtrar por director | `200` |
| 10 | `POST /carrito/<uid>` | Añadir al carrito | `201` |
| 11 | `POST /carrito/<uid>/pagar` | Pagar carrito | `200` |
| 12 | `POST /carrito/<uid>/pagar` | Saldo insuficiente | `402` |
| 13 | `POST /pelicula/<id>/voto` | Votar película | `201` |
| 14 | `POST /pelicula/<id>/voto` | Voto fuera de rango | `400` |
| 15 | `GET /pelicula/<id>/puntuacion` | Media de votos | `200` |
| 16 | `GET /ventas/<anio>/<pais>` | Ventas por año/país | `200` |
| 17 | `PUT /pelicula` | Sin token | `401` |
| 18 | `DELETE /user/<u>` | Sin token | `401` |

---

## Ejercicio 6 — Optimización (`optimizacion.sql`)

### Consulta objetivo: `GET /ventas/<anio>/<pais>`

**Estrategia:**
1. `EXPLAIN ANALYZE` de la query base → identificar seq scans.
2. Crear índice en `usuarios(pais)` → acelera filtro por país.
3. Crear índice en `pedidos(fecha_pago)` → acelera filtro por año.
4. Crear índice compuesto `pedidos(usuario_id, fecha_pago)` → cubre el JOIN + filtro.
5. `EXPLAIN ANALYZE` tras los índices → comparar coste.
6. Opcional: **vista materializada** `ventas_resumen` si el rendimiento es crítico.

**Estructura de `optimizacion.sql`:**
```sql
-- 1. EXPLAIN antes
EXPLAIN ANALYZE SELECT ...;

-- 2. Índices
CREATE INDEX idx_usuarios_pais ON usuarios(pais);
CREATE INDEX idx_pedidos_fecha_pago ON pedidos(fecha_pago);
CREATE INDEX idx_pedidos_usuario_fecha ON pedidos(usuario_id, fecha_pago);

-- 3. EXPLAIN después
EXPLAIN ANALYZE SELECT ...;

-- 4. Discusión en comentarios SQL
-- Antes: Seq Scan en usuarios (cost=...) ...
-- Después: Index Scan using idx_usuarios_pais (cost=...) ...
```

---

## Ejercicio 7 — Docker y entrega

### `docker-compose.yml` — 3 servicios

| Servicio | Imagen | Puerto | Depende de |
|---|---|---|---|
| `postgres` | `postgres:15` | `5432` | — |
| `user-svc` | `./Dockerfile` + `user.py` | `5050` | `postgres` |
| `api-svc` | `./Dockerfile` + `api.py` | `5051` | `postgres` |

Variables de entorno compartidas: `SECRET_KEY` y `DATABASE_URL`.

```
DATABASE_URL=postgresql+asyncpg://alumnodb:1234@postgres:5432/si1
```

### Entrega `P2.zip`
✅ Incluir: `user.py`, `api.py`, `client.py`, `optimizacion.sql`, `db_init.sql`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `README.txt`, `memoria.pdf`.  
❌ Excluir: `venv/`, `__pycache__/`, `.env`, `.DS_Store`.

---

## Planificación por semanas (rúbrica)

| Semana | Ejercicio | Entregable |
|---|---|---|
| **Semana 1** | Ej. 1 + Ej. 2 | `db_init.sql` (DDL + triggers + SP) |
| **Semana 2** | Ej. 3 + Ej. 4 + Ej. 5 | `user.py`, `api.py`, `client.py` |
| **Resto** | Ej. 6 + Ej. 7 | `optimizacion.sql`, Docker, `memoria.pdf`, `P2.zip` |

| Concepto | Puntos |
|---|---|
| Diseño básico de la BD | 1.5 |
| Triggers y Stored Procedures | 1.5 |
| Microservicios y API | 3.0 |
| Optimización | 1.0 |
| Cliente | 1.5 |
| Memoria | 1.5 |
| **TOTAL** | **10** |
