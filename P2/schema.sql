-- =================================================================
-- Práctica 2: Esquema Relacional, Triggers y Procedimientos Almacenados
-- Archivo: schema.sql
-- =================================================================

-- Eliminación previa de tablas en orden inverso a sus dependencias
DROP TABLE IF EXISTS votos CASCADE;
DROP TABLE IF EXISTS pedido_peliculas CASCADE;
DROP TABLE IF EXISTS pedidos CASCADE;
DROP TABLE IF EXISTS pelicula_actores CASCADE;
DROP TABLE IF EXISTS peliculas CASCADE;
DROP TABLE IF EXISTS actores CASCADE;
DROP TABLE IF EXISTS directores CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- =================================================================
-- 1. TABLAS DEL MODELO DE DATOS
-- =================================================================

-- Usuarios del sistema con saldo no negativo
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    pais VARCHAR(50) NOT NULL,
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (saldo >= 0.00)
);

-- Catálogo de directores
CREATE TABLE directores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Catálogo de actores
CREATE TABLE actores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Películas con referencia obligatoria a un director y control de stock
CREATE TABLE peliculas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    director_id INT NOT NULL REFERENCES directores(id) ON DELETE CASCADE,
    anio INT NOT NULL,
    precio NUMERIC(10, 2) NOT NULL CHECK (precio >= 0.00),
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

-- Tabla intermedia (N:M) entre películas y actores
CREATE TABLE pelicula_actores (
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    actor_id INT NOT NULL REFERENCES actores(id) ON DELETE CASCADE,
    PRIMARY KEY (pelicula_id, actor_id)
);

-- Pedidos: fecha_pago NULL representa un carrito abierto; con fecha es compra cerrada
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_pago TIMESTAMP NULL, 
    total NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0.00)
);

-- Líneas de pedido (N:M): congela precio_unitario al momento de añadir al carrito
CREATE TABLE pedido_peliculas (
    pedido_id INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0.00),
    PRIMARY KEY (pedido_id, pelicula_id)
);

-- Votos por película (0 a 10); la clave primaria compuesta restringe a un voto por usuario y film
CREATE TABLE votos (
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    puntuacion INT NOT NULL CHECK (puntuacion >= 0 AND puntuacion <= 10),
    PRIMARY KEY (usuario_id, pelicula_id)
);

-- =================================================================
-- 2. TRIGGERS DE CONSISTENCIA Y REGLAS DE NEGOCIO
-- =================================================================

-- Trigger 1: Actualiza stock al modificar el carrito (resta al insertar, devuelve al borrar)
CREATE OR REPLACE FUNCTION actualizar_stock_carrito() RETURNS TRIGGER AS $$
DECLARE
    stock_actual INT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Comprueba si hay stock disponible
        SELECT stock INTO stock_actual FROM peliculas WHERE id = NEW.pelicula_id;
        IF stock_actual < NEW.cantidad THEN
            RAISE EXCEPTION 'No hay stock suficiente para esta pelicula';
        END IF;
        -- Descuenta del stock
        UPDATE peliculas SET stock = stock - NEW.cantidad WHERE id = NEW.pelicula_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- Devuelve unidades al stock si se elimina del carrito
        UPDATE peliculas SET stock = stock + OLD.cantidad WHERE id = OLD.pelicula_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_stock
AFTER INSERT OR DELETE ON pedido_peliculas
FOR EACH ROW EXECUTE FUNCTION actualizar_stock_carrito();

-- Trigger 2: Recalcula automáticamente el importe total del pedido
CREATE OR REPLACE FUNCTION actualizar_total_pedido() RETURNS TRIGGER AS $$
DECLARE
    id_ped INT;
    suma_total NUMERIC;
BEGIN
    IF TG_OP = 'DELETE' THEN
        id_ped := OLD.pedido_id;
    ELSE
        id_ped := NEW.pedido_id;
    END IF;

    -- Suma cantidad * precio_unitario de todas las líneas del pedido
    SELECT COALESCE(SUM(cantidad * precio_unitario), 0.00) INTO suma_total
    FROM pedido_peliculas WHERE pedido_id = id_ped;

    UPDATE pedidos SET total = suma_total WHERE id = id_ped;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calcular_total_pedido
AFTER INSERT OR UPDATE OR DELETE ON pedido_peliculas
FOR EACH ROW EXECUTE FUNCTION actualizar_total_pedido();

-- Trigger 3: Valida y descuenta saldo del usuario en el momento exacto del pago
CREATE OR REPLACE FUNCTION descontar_saldo_pago() RETURNS TRIGGER AS $$
DECLARE
    saldo_usuario NUMERIC;
BEGIN
    -- Se dispara solo en la transición de pedido abierto (NULL) a pagado (NOT NULL)
    IF OLD.fecha_pago IS NULL AND NEW.fecha_pago IS NOT NULL THEN
        SELECT saldo INTO saldo_usuario FROM usuarios WHERE id = NEW.usuario_id;
        IF saldo_usuario < NEW.total THEN
            RAISE EXCEPTION 'Saldo insuficiente';
        END IF;
        UPDATE usuarios SET saldo = saldo - NEW.total WHERE id = NEW.usuario_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_descontar_saldo
BEFORE UPDATE OF fecha_pago ON pedidos
FOR EACH ROW EXECUTE FUNCTION descontar_saldo_pago();

-- =================================================================
-- 3. PROCEDIMIENTOS ALMACENADOS Y FUNCIONES
-- =================================================================

-- Calcula y retorna la calificación media (0-10) de una película
CREATE OR REPLACE FUNCTION sp_valoracion_media(id_peli INT) RETURNS NUMERIC AS $$
DECLARE
    media NUMERIC;
BEGIN
    SELECT COALESCE(AVG(puntuacion), 0.0) INTO media FROM votos WHERE pelicula_id = id_peli;
    RETURN ROUND(media, 2);
END;
$$ LANGUAGE plpgsql;

-- Finaliza la compra del carrito abierto asignando la fecha de pago actual
CREATE OR REPLACE FUNCTION sp_pagar_carrito(id_usu INT) RETURNS INT AS $$
DECLARE
    id_ped INT;
BEGIN
    -- Localiza el carrito pendiente del usuario
    SELECT id INTO id_ped FROM pedidos WHERE usuario_id = id_usu AND fecha_pago IS NULL;
    IF id_ped IS NULL THEN
        RAISE EXCEPTION 'Este usuario no tiene un carrito abierto';
    END IF;
    -- Al actualizar fecha_pago se dispara automáticamente trg_descontar_saldo
    UPDATE pedidos SET fecha_pago = CURRENT_TIMESTAMP WHERE id = id_ped;
    RETURN id_ped;
END;
$$ LANGUAGE plpgsql;