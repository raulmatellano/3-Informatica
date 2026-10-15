# Práctica 2 – Videoclub
Sistemas Informáticos - Curso 2026/2027
EPS - Universidad Autónoma de Madrid

## Descripción de la arquitectura
Para esta práctica he separado el proyecto en dos microservicios que se conectan a la misma base de datos en PostgreSQL:
- **`user.py`** (puerto 5050): Se encarga del login, registro y saldo.
- **`api.py`** (puerto 5051): Se encarga de las películas, el carrito y los pedidos.

Uso Quart para el framework asíncrono y SQLAlchemy (Core y ORM según el endpoint). La base de datos va en un contenedor de Docker. El sistema de login va por tokens (Bearer) sin guardarlos en la BD.

## Ejercicio 1 – Diseño de la Base de Datos
He creado 5 tablas principales:
- **`usuarios`**: Guarda username, contraseña (en hash), país y saldo. Le he puesto un CHECK para que el saldo no baje de 0.
- **`peliculas`**: Catálogo con el título, director, año, precio y stock. El stock no puede ser negativo.
- **`pedidos`**: Relaciona al usuario con su compra. Si `fecha_pago` es NULL, significa que es el carrito actual (abierto). Si tiene fecha, es un pedido ya pagado.
- **`pedido_peliculas`**: Tabla intermedia entre pedidos y películas. Guardo el precio aquí para que si el precio de la película cambia en el futuro, no afecte a los pedidos antiguos.
- **`votos`**: Relación entre usuario y película para las puntuaciones (CHECK entre 0 y 10).

## Ejercicio 2 – Triggers y Funciones
Para asegurar la consistencia he programado estos Triggers:
1. **`trg_actualizar_stock`**: Al añadir una peli al carrito, quita 1 del stock. Si se borra del carrito, lo devuelve. Si no hay stock, lanza un error.
2. **`trg_calcular_total_pedido`**: Cada vez que se mete o saca algo del carrito, recalcula la suma total de ese pedido.
3. **`trg_descontar_saldo`**: Al rellenar la `fecha_pago` del pedido, mira si el usuario tiene saldo suficiente. Si tiene, se lo resta. Si no, salta una excepción y bloquea el update.

Y estos dos Procedimientos Almacenados (SPs):
- **`sp_valoracion_media`**: Le pasas el id de una película y te devuelve la nota media.
- **`sp_pagar_carrito`**: Le pasas el id de un usuario. Busca su pedido con fecha en NULL y le pone la fecha actual. Esto hace saltar el trigger del saldo automáticamente.

## Ejercicio 3 – Microservicio de Usuarios (user.py)
Utiliza SQLAlchemy ORM.
- `PUT /user` -> Crea el usuario.
- `POST /user/login` -> Comprueba contraseña y devuelve el token.
- `POST /user/logout` -> Cierra sesión.
- `DELETE /user/<username>` -> Borra el usuario.
- `PATCH /user/<username>/saldo` -> Actualiza el dinero.

## Ejercicio 4 – Microservicio Principal (api.py)
Utiliza SQLAlchemy Core (con text y execute). Cada consulta a la BD se hace en un solo execute.
- `PUT /pelicula` y `DELETE /pelicula/<id>` -> Gestión del catálogo.
- `GET /peliculas` -> Búsquedas (por año, director...).
- `POST /carrito/<user_id>` -> Mete una película en el pedido sin pagar.
- `POST /carrito/<user_id>/pagar` -> Llama al procedimiento almacenado para pagar.
- `GET /pedidos/<user_id>` -> Historial de compras.
- `POST /pelicula/<id>/voto` y `GET /pelicula/<id>/puntuacion` -> Votos y media.

**Endpoint de ventas:** `GET /ventas/<anio>/<pais>`  
Esta es la consulta base que saco con un solo execute haciendo JOINs entre pedidos, usuarios, pedido_peliculas y peliculas, filtrando por año y país.

## Ejercicio 6 – Optimización
Para mejorar la query de ventas, hice un `EXPLAIN ANALYZE` y vi que hacía un escaneo secuencial (Seq Scan) de toda la tabla. Para solucionarlo y que vaya más rápido (Index Scan), he creado dos índices: uno para el país en los usuarios y otro para la fecha de pago en los pedidos. Están explicados en `optimizacion.sql`.