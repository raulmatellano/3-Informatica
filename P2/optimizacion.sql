-- ============================================================================
-- Ejercicio 6: Optimización de Consultas con Índices
-- Archivo: optimizacion.sql
-- ============================================================================

-- 1. EXPLAIN ANALYZE ANTES DE LOS ÍNDICES
-- Sin índices, el optimizador recurre a lecturas secuenciales completas (Seq Scan)
-- para evaluar los filtros de 'pais' y 'fecha_pago', aumentando el coste en tablas grandes.

EXPLAIN ANALYZE
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE EXTRACT(YEAR FROM ped.fecha_pago) = 2026 
  AND u.pais = 'España' 
  AND ped.fecha_pago IS NOT NULL;


-- 2. CREACIÓN DE ÍNDICES ESTRATÉGICOS
-- Agilizan el filtrado y el emparejamiento de claves foráneas en los JOINs.

-- Índice en 'pais' para acelerar el filtro por nacionalidad (u.pais = 'España')
CREATE INDEX idx_usuarios_pais ON usuarios(pais);

-- Índice en 'fecha_pago' para optimizar filtros temporales en pedidos
CREATE INDEX idx_pedidos_fecha_pago ON pedidos(fecha_pago);

-- Índice compuesto (usuario_id, fecha_pago) para optimizar el JOIN con usuarios y el filtro de fecha
CREATE INDEX idx_pedidos_usuario_fecha ON pedidos(usuario_id, fecha_pago);


-- 3. EXPLAIN ANALYZE DESPUÉS DE LOS ÍNDICES
-- El optimizador sustituye el Seq Scan por búsquedas mediante índice (Index Scan / Bitmap Index Scan),
-- accediendo solo a las tuplas que cumplen el filtro y reduciendo el tiempo de ejecución.

EXPLAIN ANALYZE
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE EXTRACT(YEAR FROM ped.fecha_pago) = 2026 
  AND u.pais = 'España' 
  AND ped.fecha_pago IS NOT NULL;