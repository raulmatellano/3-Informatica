EXPLAIN ANALYZE 
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE ped.fecha_pago >= '2026-01-01' AND ped.fecha_pago < '2027-01-01'
  AND u.pais = 'España'
  AND ped.fecha_pago IS NOT NULL;

CREATE INDEX idx_usuarios_pais ON usuarios(pais);

CREATE INDEX idx_pedidos_fecha_pago ON pedidos(fecha_pago);

CREATE INDEX idx_pedidos_usuario_fecha ON pedidos(usuario_id, fecha_pago);

EXPLAIN ANALYZE 
SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
FROM pedidos ped 
JOIN usuarios u ON ped.usuario_id = u.id 
JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
JOIN peliculas p ON pp.pelicula_id = p.id 
WHERE ped.fecha_pago >= '2026-01-01' AND ped.fecha_pago < '2027-01-01'
  AND u.pais = 'España'
  AND ped.fecha_pago IS NOT NULL;