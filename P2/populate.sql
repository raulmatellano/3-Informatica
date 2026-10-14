-- ============================================================================
-- PRÁCTICA 2: SISTEMAS INFORMÁTICOS - VIDEOCLUB
-- ARCHIVO: populate.sql (Carga de datos de prueba)
-- ============================================================================

-- Limpieza de datos previos
DELETE FROM votos;
DELETE FROM pedido_peliculas;
DELETE FROM pedidos;
DELETE FROM peliculas;
DELETE FROM usuarios;

-- 1. USUARIOS
-- Usuarios con distintos países (Francia, España, Alemania) y saldos variados para pruebas.
-- La contraseña de todos es '1234' (en hash SHA-256).
INSERT INTO usuarios (id, username, password_hash, pais, saldo) VALUES
    (1, 'jean_dupont',   '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia', 100.00),
    (2, 'pierre_curie',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia',  50.00),
    (3, 'marie_claire',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Francia',   0.00),
    (4, 'carlos_garcia', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'España',  150.00),
    (5, 'lucia_martin',  '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'España',   20.00),
    (6, 'hans_gruber',   '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Alemania', 80.00);

-- 2. PELÍCULAS
-- Catálogo con directores y años variados. La película 9 tiene stock 0 para probar errores.
INSERT INTO peliculas (id, titulo, director, anio, precio, stock) VALUES
    (1, 'Oppenheimer',        'Christopher Nolan', 2023, 14.99, 20),
    (2, 'Inception',          'Christopher Nolan', 2010,  9.99, 30),
    (3, 'Interstellar',       'Christopher Nolan', 2014, 11.99, 25),
    (4, 'Pulp Fiction',       'Quentin Tarantino', 1994,  8.50, 15),
    (5, 'Django Unchained',   'Quentin Tarantino', 2012,  9.99, 10),
    (6, 'Dune: Part Two',     'Denis Villeneuve',  2024, 15.99, 20),
    (7, 'Dolor y Gloria',     'Pedro Almodóvar',   2019,  8.00, 12),
    (8, 'El Viaje de Chihiro','Hayao Miyazaki',    2001,  8.99, 18),
    (9, 'Sin Stock',          'Anonimo',           2025,  5.00,  0);

-- 3. PEDIDOS
-- Pedidos pagados en 2026 y 2025 (para el endpoint de ventas) y pedido 5 como carrito abierto.
INSERT INTO pedidos (id, usuario_id, fecha_pago, total) VALUES
    (1, 1, '2026-02-14 18:30:00', 0.00), -- jean_dupont (Francia, 2026)
    (2, 2, '2026-03-20 20:15:00', 0.00), -- pierre_curie (Francia, 2026)
    (3, 1, '2025-11-10 12:00:00', 0.00), -- jean_dupont (Francia, 2025)
    (4, 4, '2026-01-05 10:45:00', 0.00), -- carlos_garcia (España, 2026)
    (5, 5, NULL,                  0.00); -- lucia_martin (carrito abierto sin pagar)

-- 4. PEDIDO_PELICULAS
-- Artículos incluidos en cada pedido. Al insertar, el trigger actualiza el total automáticamente.
INSERT INTO pedido_peliculas (pedido_id, pelicula_id, cantidad, precio_unitario) VALUES
    (1, 1, 1, 14.99), -- Oppenheimer (14.99)
    (1, 2, 1,  9.99), -- Inception (9.99) -> Total = 24.98
    (2, 1, 1, 14.99), -- Oppenheimer -> Total = 14.99
    (3, 2, 1,  9.99), -- Inception -> Total = 9.99
    (4, 3, 1, 11.99), -- Interstellar (11.99)
    (4, 6, 1, 15.99), -- Dune 2 (15.99) -> Total = 27.98
    (5, 6, 1, 15.99); -- Carrito de Lucía: Dune 2 (15.99)

-- 5. VOTOS
-- Valoraciones de 0 a 10 para probar la función de nota media.
INSERT INTO votos (usuario_id, pelicula_id, puntuacion) VALUES
    (1, 1, 10), -- Oppenheimer (Media: 9.50)
    (2, 1,  9),
    (4, 2,  8), -- Inception (Media: 8.50)
    (6, 2,  9),
    (1, 4, 10), -- Pulp Fiction (Media: 9.00)
    (4, 4,  8);

-- Sincronizar contadores de IDs
SELECT setval('usuarios_id_seq', (SELECT MAX(id) FROM usuarios));
SELECT setval('peliculas_id_seq', (SELECT MAX(id) FROM peliculas));
SELECT setval('pedidos_id_seq', (SELECT MAX(id) FROM pedidos));
