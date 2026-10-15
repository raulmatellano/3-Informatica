-- =================================================================
-- Práctica 2: Población de Datos Iniciales para Pruebas
-- Archivo: populate.sql
-- =================================================================

-- 0. Limpieza previa de datos en orden inverso a dependencias de clave foránea
DELETE FROM votos;
DELETE FROM pedido_peliculas;
DELETE FROM pedidos;
DELETE FROM pelicula_actores;
DELETE FROM peliculas;
DELETE FROM actores;
DELETE FROM directores;
DELETE FROM usuarios;

-- 1. Usuarios de prueba (contraseña por defecto hasheada con SHA-256)
INSERT INTO usuarios (id, username, password_hash, pais, saldo) VALUES
    (1, 'jean_dupont',   '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia', 100.00),
    (2, 'pierre_curie',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia',  50.00),
    (3, 'marie_claire',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia',   0.00),
    (4, 'carlos_garcia', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'España',  150.00),
    (5, 'lucia_martin',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'España',   20.00),
    (6, 'hans_gruber',   '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Alemania', 80.00);

-- 2. Directores
INSERT INTO directores (id, nombre) VALUES
    (1, 'Christopher Nolan'),
    (2, 'Quentin Tarantino'),
    (3, 'Denis Villeneuve'),
    (4, 'Pedro Almodovar'),
    (5, 'Hayao Miyazaki');

-- 3. Actores
INSERT INTO actores (id, nombre) VALUES
    (1, 'Cillian Murphy'),
    (2, 'Leonardo DiCaprio'),
    (3, 'Matthew McConaughey'),
    (4, 'John Travolta'),
    (5, 'Timothee Chalamet'),
    (6, 'Antonio Banderas');

-- 4. Películas (con director asociado, stock y precio)
INSERT INTO peliculas (id, titulo, director_id, anio, precio, stock) VALUES
    (1, 'Oppenheimer',        1, 2023, 14.99, 20),
    (2, 'Inception',          1, 2010,  9.99, 30),
    (3, 'Interstellar',       1, 2014, 11.99, 25),
    (4, 'Pulp Fiction',       2, 1994,  8.50, 15),
    (5, 'Dune: Part Two',     3, 2024, 15.99, 20),
    (6, 'Dolor y Gloria',     4, 2019,  8.00, 12),
    (7, 'El Viaje de Chihiro',5, 2001,  8.99, 18);

-- 5. Reparto de películas (relación N:M pelicula_actores)
INSERT INTO pelicula_actores (pelicula_id, actor_id) VALUES
    (1, 1), -- Oppenheimer -> Cillian Murphy
    (2, 2), -- Inception -> Leonardo DiCaprio
    (2, 1), -- Inception -> Cillian Murphy
    (3, 3), -- Interstellar -> McConaughey
    (4, 4), -- Pulp Fiction -> Travolta
    (5, 5), -- Dune -> Chalamet
    (6, 6); -- Dolor y Gloria -> Banderas

-- 6. Pedidos (pedidos 1-3 pagados, pedido 4 carrito abierto con fecha NULL)
INSERT INTO pedidos (id, usuario_id, fecha_pago, total) VALUES
    (1, 1, '2026-02-14 18:30:00', 0.00), 
    (2, 2, '2026-03-20 20:15:00', 0.00), 
    (3, 4, '2026-01-05 10:45:00', 0.00), 
    (4, 5, NULL,                  0.00);

-- Líneas de cada pedido con precio unitario registrado
INSERT INTO pedido_peliculas (pedido_id, pelicula_id, cantidad, precio_unitario) VALUES
    (1, 1, 1, 14.99),
    (1, 2, 1,  9.99), 
    (2, 1, 1, 14.99), 
    (3, 3, 1, 11.99), 
    (4, 5, 1, 15.99); 

-- 7. Calificaciones de usuarios a películas
INSERT INTO votos (usuario_id, pelicula_id, puntuacion) VALUES
    (1, 1, 10),
    (2, 1,  9),
    (4, 2,  8),
    (1, 4, 10);

-- 8. Sincronización de secuencias SERIAL con el ID máximo insertado manualmente
SELECT setval('usuarios_id_seq', (SELECT MAX(id) FROM usuarios));
SELECT setval('directores_id_seq', (SELECT MAX(id) FROM directores));
SELECT setval('actores_id_seq', (SELECT MAX(id) FROM actores));
SELECT setval('peliculas_id_seq', (SELECT MAX(id) FROM peliculas));
SELECT setval('pedidos_id_seq', (SELECT MAX(id) FROM pedidos));