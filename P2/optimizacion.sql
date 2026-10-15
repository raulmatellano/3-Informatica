-- ============================================================================
-- Ejercicio 6: Optimizacion
-- ============================================================================

-- 1. Lo primero fue hacer un EXPLAIN ANALYZE para ver que fallaba
-- Vi que PostgreSQL hacia un "Seq Scan" (escanear toda la tabla fila a fila) 
-- porque tenia que buscar por pais y por fecha en unas tablas grandes.
EXPLAIN ANALYZE 
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE EXTRACT(YEAR FROM ped.fecha_pago) = 2026 
  AND u.pais = 'Espana' 
  AND ped.fecha_pago IS NOT NULL;

-- 2. Crear indices
-- Para arreglarlo, he creado un indice para buscar rapido por pais en usuarios
CREATE INDEX idx_usuarios_pais ON usuarios(pais);

-- He creado otro indice para la fecha de pago en los pedidos
CREATE INDEX idx_pedidos_fecha_pago ON pedidos(fecha_pago);

-- Y un indice compuesto por si acaso se busca por usuario y fecha a la vez
CREATE INDEX idx_pedidos_usuario_fecha ON pedidos(usuario_id, fecha_pago);

-- 3. EXPLAIN ANALYZE final
-- Despues de crear los indices, al hacer la misma consulta, PostgreSQL
-- usa "Index Scan" o "Bitmap Index Scan", lo que hace que vaya super rapido
-- porque ya no tiene que leer toda la tabla entera.
EXPLAIN ANALYZE 
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE EXTRACT(YEAR FROM ped.fecha_pago) = 2026 
  AND u.pais = 'Espana' 
  AND ped.fecha_pago IS NOT NULL;