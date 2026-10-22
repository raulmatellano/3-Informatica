DROP TABLE IF EXISTS votos CASCADE;
DROP TABLE IF EXISTS pedido_peliculas CASCADE;
DROP TABLE IF EXISTS pedidos CASCADE;
DROP TABLE IF EXISTS pelicula_actores CASCADE;
DROP TABLE IF EXISTS peliculas CASCADE;
DROP TABLE IF EXISTS actores CASCADE;
DROP TABLE IF EXISTS directores CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

DROP FUNCTION IF EXISTS actualizar_stock_carrito() CASCADE;
DROP FUNCTION IF EXISTS actualizar_total_pedido() CASCADE;
DROP FUNCTION IF EXISTS descontar_saldo_pago() CASCADE;
DROP FUNCTION IF EXISTS sp_valoracion_media(INT) CASCADE;
DROP FUNCTION IF EXISTS sp_pagar_carrito(INT) CASCADE;

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    pais VARCHAR(50) NOT NULL,
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (saldo >= 0.00)
);

CREATE TABLE directores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

CREATE TABLE actores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

CREATE TABLE peliculas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    director_id INT NOT NULL REFERENCES directores(id) ON DELETE CASCADE,
    anio INT NOT NULL,
    precio NUMERIC(10, 2) NOT NULL CHECK (precio >= 0.00),
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE pelicula_actores (
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    actor_id INT NOT NULL REFERENCES actores(id) ON DELETE CASCADE,
    PRIMARY KEY (pelicula_id, actor_id)
);

CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_pago TIMESTAMP NULL, 
    total NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0.00)
);

CREATE TABLE pedido_peliculas (
    pedido_id INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0.00),
    PRIMARY KEY (pedido_id, pelicula_id)
);

CREATE TABLE votos (
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    puntuacion INT NOT NULL CHECK (puntuacion >= 0 AND puntuacion <= 10),
    PRIMARY KEY (usuario_id, pelicula_id)
);

-- Controla el stock: resta cuando metemos al carrito y suma si lo borramos
CREATE OR REPLACE FUNCTION actualizar_stock_carrito() RETURNS TRIGGER AS $$
DECLARE
    stock_actual INT;
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT stock INTO stock_actual FROM peliculas WHERE id = NEW.pelicula_id;
        IF stock_actual < NEW.cantidad THEN
            RAISE EXCEPTION 'No hay stock suficiente para esta pelicula';
        END IF;
        
        UPDATE peliculas SET stock = stock - NEW.cantidad WHERE id = NEW.pelicula_id;
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE peliculas SET stock = stock + OLD.cantidad WHERE id = OLD.pelicula_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_stock
AFTER INSERT OR DELETE ON pedido_peliculas
FOR EACH ROW EXECUTE FUNCTION actualizar_stock_carrito();

-- Recalcula el total del pedido sumando todas las pelis que tiene
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

    SELECT SUM(cantidad * precio_unitario) INTO suma_total FROM pedido_peliculas WHERE pedido_id = id_ped;
    
    IF suma_total IS NULL THEN
        suma_total := 0.00;
    END IF;

    UPDATE pedidos SET total = suma_total WHERE id = id_ped;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calcular_total_pedido
AFTER INSERT OR UPDATE OR DELETE ON pedido_peliculas
FOR EACH ROW EXECUTE FUNCTION actualizar_total_pedido();

-- Al pagar el pedido comprueba que el usuario tenga saldo y se lo resta
CREATE OR REPLACE FUNCTION descontar_saldo_pago() RETURNS TRIGGER AS $$
DECLARE
    saldo_usuario NUMERIC;
BEGIN
    IF OLD.fecha_pago IS NULL AND NEW.fecha_pago IS NOT NULL THEN
        SELECT saldo INTO saldo_usuario FROM usuarios WHERE id = NEW.usuario_id;
        
        IF saldo_usuario < NEW.total THEN
            RAISE EXCEPTION 'El usuario no tiene saldo suficiente';
        END IF;
        
        UPDATE usuarios SET saldo = saldo - NEW.total WHERE id = NEW.usuario_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_descontar_saldo
BEFORE UPDATE OF fecha_pago ON pedidos
FOR EACH ROW EXECUTE FUNCTION descontar_saldo_pago();

-- Calcula la media de las puntuaciones que tiene una pelicula
CREATE OR REPLACE FUNCTION sp_valoracion_media(id_peli INT) RETURNS NUMERIC AS $$
DECLARE
    media NUMERIC;
BEGIN
    SELECT AVG(puntuacion) INTO media FROM votos WHERE pelicula_id = id_peli;
    IF media IS NULL THEN
        media := 0.0;
    END IF;
    RETURN ROUND(media, 2);
END;
$$ LANGUAGE plpgsql;

-- Pone fecha de pago al carrito abierto para cobrarlo
CREATE OR REPLACE FUNCTION sp_pagar_carrito(id_usu INT) RETURNS INT AS $$
DECLARE
    id_ped INT;
BEGIN
    SELECT id INTO id_ped FROM pedidos WHERE usuario_id = id_usu AND fecha_pago IS NULL;
    
    IF id_ped IS NULL THEN
        RAISE EXCEPTION 'Este usuario no tiene ningun carrito abierto';
    END IF;

    UPDATE pedidos SET fecha_pago = CURRENT_TIMESTAMP WHERE id = id_ped;
    RETURN id_ped;
END;
$$ LANGUAGE plpgsql;