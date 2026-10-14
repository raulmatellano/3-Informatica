-- ============================================================================
-- PRÁCTICA 2: SISTEMAS INFORMÁTICOS - VIDEOCLUB
-- ARCHIVO: schema.sql (Tablas, triggers y procedimientos)
-- ============================================================================

-- Limpieza preventiva de tablas y funciones
DROP TABLE IF EXISTS votos CASCADE;
DROP TABLE IF EXISTS pedido_peliculas CASCADE;
DROP TABLE IF EXISTS pedidos CASCADE;
DROP TABLE IF EXISTS peliculas CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

DROP FUNCTION IF EXISTS actualizar_stock_carrito() CASCADE;
DROP FUNCTION IF EXISTS actualizar_total_pedido() CASCADE;
DROP FUNCTION IF EXISTS descontar_saldo_pago() CASCADE;
DROP FUNCTION IF EXISTS sp_valoracion_media(INT) CASCADE;
DROP FUNCTION IF EXISTS sp_pagar_carrito(INT) CASCADE;


-- ============================================================================
-- TABLAS
-- ============================================================================

-- TABLA: usuarios
-- - Por qué: Guarda usuarios con país (para filtrar ventas) y saldo exacto.
-- - Cómo: username UNIQUE, contraseña en hash SHA-256 y saldo NUMERIC >= 0.
-- - Para qué: Registro, login y control de fondos del cliente.
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    pais VARCHAR(50) NOT NULL,
    saldo NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (saldo >= 0.00)
);

-- TABLA: peliculas
-- - Por qué: Catálogo con los campos requeridos (título, director, año, precio, stock).
-- - Cómo: Clave id autoincremental y CHECKs para que precio y stock nunca sean negativos.
-- - Para qué: Búsquedas por director/año y control de copias disponibles.
CREATE TABLE peliculas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(100) NOT NULL,
    director VARCHAR(100) NOT NULL,
    anio INT NOT NULL,
    precio NUMERIC(10, 2) NOT NULL CHECK (precio >= 0.00),
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

-- TABLA: pedidos (Carrito y compras)
-- - Por qué: Un pedido con fecha_pago NULL es un carrito abierto; al pagar se rellena la fecha.
-- - Cómo: Clave foránea usuario_id y total calculado automáticamente por triggers.
-- - Para qué: Manejar carritos de compra y registrar el histórico de ventas.
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_pago TIMESTAMP NULL,
    total NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0.00)
);

-- TABLA: pedido_peliculas (Líneas del pedido)
-- - Por qué: Relación N:M entre pedidos y películas. Congela el precio al añadir al carrito.
-- - Cómo: PK compuesta (pedido_id, pelicula_id) y cantidad > 0.
-- - Para qué: Detallar productos, cantidades y precios de cada compra.
CREATE TABLE pedido_peliculas (
    pedido_id INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0.00),
    PRIMARY KEY (pedido_id, pelicula_id)
);

-- TABLA: votos
-- - Por qué: Un único voto por usuario y película con nota entre 0 y 10.
-- - Cómo: PK compuesta (usuario_id, pelicula_id) y CHECK (puntuacion BETWEEN 0 AND 10).
-- - Para qué: Almacenar notas para calcular la valoración media.
CREATE TABLE votos (
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pelicula_id INT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    puntuacion INT NOT NULL CHECK (puntuacion >= 0 AND puntuacion <= 10),
    PRIMARY KEY (usuario_id, pelicula_id)
);


-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- TRIGGER: Control de stock al añadir o quitar del carrito
-- - Por qué: Requisito de mantener el stock actualizado al modificar el carrito.
-- - Cómo: En INSERT valida y descuenta stock; en DELETE devuelve las unidades.
-- - Para qué: Evitar comprar películas agotadas sin gestionar stock a mano en Python.
CREATE OR REPLACE FUNCTION actualizar_stock_carrito()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF (SELECT stock FROM peliculas WHERE id = NEW.pelicula_id) < NEW.cantidad THEN
            RAISE EXCEPTION 'No hay suficiente stock para la pelicula %', NEW.pelicula_id;
        END IF;

        UPDATE peliculas
        SET stock = stock - NEW.cantidad
        WHERE id = NEW.pelicula_id;

        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE peliculas
        SET stock = stock + OLD.cantidad
        WHERE id = OLD.pelicula_id;

        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_stock
AFTER INSERT OR DELETE ON pedido_peliculas
FOR EACH ROW
EXECUTE FUNCTION actualizar_stock_carrito();

-- TRIGGER: Actualizar total del pedido automáticamente
-- - Por qué: Requisito de mantener el precio final del carrito actualizado.
-- - Cómo: Suma cantidad * precio_unitario de las líneas del pedido.
-- - Para qué: Tener el total del carrito siempre sincronizado.
CREATE OR REPLACE FUNCTION actualizar_total_pedido()
RETURNS TRIGGER AS $$
DECLARE
    v_pedido_id INT;
BEGIN
    IF (TG_OP = 'DELETE') THEN
        v_pedido_id := OLD.pedido_id;
    ELSE
        v_pedido_id := NEW.pedido_id;
    END IF;

    UPDATE pedidos
    SET total = COALESCE((
        SELECT SUM(cantidad * precio_unitario)
        FROM pedido_peliculas
        WHERE pedido_id = v_pedido_id
    ), 0.00)
    WHERE id = v_pedido_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_actualizar_total
AFTER INSERT OR UPDATE OR DELETE ON pedido_peliculas
FOR EACH ROW
EXECUTE FUNCTION actualizar_total_pedido();

-- TRIGGER: Descontar saldo al pagar el carrito
-- - Por qué: Requisito de descontar el coste automáticamente del saldo del cliente al pagar.
-- - Cómo: Al rellenar fecha_pago, comprueba saldo del usuario, descuenta el total o lanza error.
-- - Para qué: Asegurar que solo se paga si hay fondos y actualizar el saldo en la BD.
CREATE OR REPLACE FUNCTION descontar_saldo_pago()
RETURNS TRIGGER AS $$
DECLARE
    v_saldo NUMERIC(10, 2);
BEGIN
    IF OLD.fecha_pago IS NULL AND NEW.fecha_pago IS NOT NULL THEN
        SELECT saldo INTO v_saldo
        FROM usuarios
        WHERE id = NEW.usuario_id;

        IF v_saldo < NEW.total THEN
            RAISE EXCEPTION 'Saldo insuficiente. Saldo actual: %, Total a pagar: %', v_saldo, NEW.total;
        END IF;

        UPDATE usuarios
        SET saldo = saldo - NEW.total
        WHERE id = NEW.usuario_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_descontar_saldo
BEFORE UPDATE OF fecha_pago ON pedidos
FOR EACH ROW
EXECUTE FUNCTION descontar_saldo_pago();


-- ============================================================================
-- PROCEDIMIENTOS ALMACENADOS Y FUNCIONES (SPs)
-- ============================================================================

-- PROCEDIMIENTO / FUNCIÓN: Valoración media de una película
-- - Por qué: Requisito de calcular el promedio de votos mediante procedimientos almacenados.
-- - Cómo: SELECT AVG(puntuacion) redondeado a 2 decimales (o 0 si no hay votos).
-- - Para qué: Consultar la nota media de una película en una sola llamada.
CREATE OR REPLACE FUNCTION sp_valoracion_media(p_pelicula_id INT)
RETURNS NUMERIC AS $$
DECLARE
    v_media NUMERIC;
BEGIN
    SELECT COALESCE(AVG(puntuacion), 0.0)
    INTO v_media
    FROM votos
    WHERE pelicula_id = p_pelicula_id;

    RETURN ROUND(v_media, 2);
END;
$$ LANGUAGE plpgsql;

-- PROCEDIMIENTO / FUNCIÓN: Pagar el carrito de un usuario
-- - Por qué: Encapsula el pago del carrito en una operación simple.
-- - Cómo: Asigna fecha_pago = CURRENT_TIMESTAMP al carrito abierto, activando el trigger de saldo.
-- - Para qué: Pagar el carrito desde Python con una sola consulta.
CREATE OR REPLACE FUNCTION sp_pagar_carrito(p_usuario_id INT)
RETURNS INT AS $$
DECLARE
    v_pedido_id INT;
BEGIN
    SELECT id INTO v_pedido_id
    FROM pedidos
    WHERE usuario_id = p_usuario_id AND fecha_pago IS NULL;

    IF v_pedido_id IS NULL THEN
        RAISE EXCEPTION 'El usuario % no tiene ningun carrito abierto', p_usuario_id;
    END IF;

    UPDATE pedidos
    SET fecha_pago = CURRENT_TIMESTAMP
    WHERE id = v_pedido_id;

    RETURN v_pedido_id;
END;
$$ LANGUAGE plpgsql;
