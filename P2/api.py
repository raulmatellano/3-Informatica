"""
Microservicio principal de la API del videoclub (Puerto 5051).
Gestiona películas, carritos, pedidos, votos y ventas.
Implementado con Quart y consultas directas en SQLAlchemy Core.
"""
import os
import hashlib
import hmac
import base64
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

app = Quart(__name__)

# Configuración de base de datos y clave para verificación de tokens
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:9999/si1")
SECRET_KEY = os.getenv("SECRET_KEY", "clave_super_secreta_para_la_practica")

# Conexión asíncrona a PostgreSQL con SQLAlchemy Core
engine = create_async_engine(DATABASE_URL, echo=False)

# Valida cabecera 'Authorization: Bearer <token>' usando HMAC-SHA256
def verificar_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    try:
        token_b64 = auth_header.split(" ")[1]
        token_raw = base64.b64decode(token_b64).decode()
        username, firma_recibida = token_raw.split(":")
        
        firma_calculada = hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
        
        if firma_calculada == firma_recibida:
            return username
    except:
        pass
    return None

# =================================================================
# 4.1 GESTIÓN DE PELÍCULAS
# =================================================================

# PUT /pelicula: Da de alta una película asociada a un director existente
@app.route('/pelicula', methods=['PUT'])
async def crear_pelicula():
    # Requiere autenticación
    usuario = verificar_token(request.headers.get("Authorization"))
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401
        
    datos = await request.get_json()
    
    async with engine.begin() as conn:
        # Inserta película recibiendo director_id y devuelve el ID generado
        consulta = text("""
            INSERT INTO peliculas (titulo, director_id, anio, precio, stock) 
            VALUES (:t, :d_id, :a, :p, :s) 
            RETURNING id
        """)
        resultado = await conn.execute(consulta, {
            "t": datos['titulo'],
            "d_id": datos['director_id'],
            "a": datos['anio'],
            "p": datos['precio'],
            "s": datos['stock']
        })
        nuevo_id = resultado.scalar()
        
        return jsonify({"pelicula_id": nuevo_id}), 201

# DELETE /pelicula/<id>: Elimina una película por su identificador
@app.route('/pelicula/<int:id>', methods=['DELETE'])
async def borrar_pelicula(id):
    # Requiere autenticación
    usuario = verificar_token(request.headers.get("Authorization"))
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401
        
    async with engine.begin() as conn:
        # Borra en cascada referencias asociadas según el esquema
        consulta = text("DELETE FROM peliculas WHERE id = :id")
        await conn.execute(consulta, {"id": id})
        return jsonify({"mensaje": "Pelicula borrada"}), 200

# GET /peliculas: Consulta catálogo con filtros opcionales de director y año
@app.route('/peliculas', methods=['GET'])
async def buscar_peliculas():
    director_id = request.args.get('director_id')
    anio = request.args.get('anio')
    
    async with engine.connect() as conn:
        # Une directores y actores; usa STRING_AGG para agrupar actores en un solo string
        sql = """
            SELECT p.id, p.titulo, d.nombre AS director, p.anio, p.precio, p.stock,
                   COALESCE(STRING_AGG(a.nombre, ', '), '') AS actores
            FROM peliculas p
            JOIN directores d ON p.director_id = d.id
            LEFT JOIN pelicula_actores pa ON p.id = pa.pelicula_id
            LEFT JOIN actores a ON pa.actor_id = a.id
            WHERE 1=1
        """
        parametros = {}
        
        # Filtros dinámicos según query params
        if director_id:
            sql += " AND p.director_id = :dir"
            parametros['dir'] = int(director_id)
        if anio:
            sql += " AND p.anio = :anio"
            parametros['anio'] = int(anio)
            
        # Agrupación requerida por la función agregada STRING_AGG
        sql += " GROUP BY p.id, p.titulo, d.nombre, p.anio, p.precio, p.stock"
            
        resultado = await conn.execute(text(sql), parametros)
        peliculas = []
        for fila in resultado:
            peliculas.append({
                "id": fila.id,
                "titulo": fila.titulo,
                "director": fila.director,
                "actores": fila.actores,
                "anio": fila.anio,
                "precio": float(fila.precio),
                "stock": fila.stock
            })
            
        return jsonify(peliculas), 200

# =================================================================
# 4.2 CARRITO Y PEDIDOS
# =================================================================

# POST /carrito/<user_id>: Añade película al carrito abierto (dispara trigger de stock)
@app.route('/carrito/<int:user_id>', methods=['POST'])
async def anadir_al_carrito(user_id):
    usuario = verificar_token(request.headers.get("Authorization"))
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    pelicula_id = datos['pelicula_id']
    cantidad = datos.get('cantidad', 1)

    async with engine.begin() as conn:
        # Busca si ya tiene un carrito abierto (pedido con fecha_pago NULL)
        res_pedido = await conn.execute(
            text("SELECT id FROM pedidos WHERE usuario_id = :uid AND fecha_pago IS NULL"), 
            {"uid": user_id}
        )
        pedido_id = res_pedido.scalar()

        # Si no existe carrito abierto, se crea uno nuevo
        if not pedido_id:
            res_nuevo = await conn.execute(
                text("INSERT INTO pedidos (usuario_id) VALUES (:uid) RETURNING id"),
                {"uid": user_id}
            )
            pedido_id = res_nuevo.scalar()

        # Obtiene el precio actual para congelarlo en la línea del pedido
        res_precio = await conn.execute(
            text("SELECT precio FROM peliculas WHERE id = :pid"), 
            {"pid": pelicula_id}
        )
        precio = res_precio.scalar()

        # Inserta línea en pedido_peliculas (dispara trg_actualizar_stock y trg_calcular_total_pedido)
        await conn.execute(
            text("""
                INSERT INTO pedido_peliculas (pedido_id, pelicula_id, cantidad, precio_unitario) 
                VALUES (:ped_id, :pel_id, :cant, :precio)
            """), 
            {"ped_id": pedido_id, "pel_id": pelicula_id, "cant": cantidad, "precio": precio}
        )
        
        return jsonify({"mensaje": "Añadido al carrito"}), 201

# POST /carrito/<user_id>/pagar: Cierra el carrito llamando a sp_pagar_carrito()
@app.route('/carrito/<int:user_id>/pagar', methods=['POST'])
async def pagar_carrito(user_id):
    usuario = verificar_token(request.headers.get("Authorization"))
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401

    async with engine.begin() as conn:
        try:
            # Ejecuta SP que asigna fecha_pago (dispara trigger de descuento de saldo)
            await conn.execute(text("SELECT sp_pagar_carrito(:uid)"), {"uid": user_id})
            return jsonify({"mensaje": "Pago completado correctamente"}), 200
        except Exception as e:
            # Si el saldo es insuficiente o no hay carrito, devuelve 402
            return jsonify({"error": str(e)}), 402

# GET /pedidos/<user_id>: Devuelve el historial de pedidos de un cliente
@app.route('/pedidos/<int:user_id>', methods=['GET'])
async def ver_pedidos(user_id):
    usuario = verificar_token(request.headers.get("Authorization"))
    if not usuario:
        return jsonify({"error": "No autorizado"}), 401

    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT id, fecha_pago, total FROM pedidos WHERE usuario_id = :uid"), 
            {"uid": user_id}
        )
        
        pedidos = []
        for fila in res:
            pedidos.append({
                "pedido_id": fila.id,
                "fecha_pago": fila.fecha_pago.isoformat() if fila.fecha_pago else None,
                "total": float(fila.total)
            })
            
        return jsonify(pedidos), 200

# =================================================================
# 4.3 VOTOS
# =================================================================

# POST /pelicula/<id>/voto: Registra puntuación del 0 al 10 para una película
@app.route('/pelicula/<int:id>/voto', methods=['POST'])
async def votar_pelicula(id):
    usuario_autenticado = verificar_token(request.headers.get("Authorization"))
    if not usuario_autenticado:
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    puntos = datos['puntuacion']
    
    # Validación de rango de puntuación
    if puntos < 0 or puntos > 10:
        return jsonify({"error": "Nota no valida"}), 400

    async with engine.begin() as conn:
        # Obtiene el ID numérico del usuario autenticado
        res_usu = await conn.execute(
            text("SELECT id FROM usuarios WHERE username = :usr"),
            {"usr": usuario_autenticado}
        )
        user_id = res_usu.scalar()

        try:
            # Inserta voto (la clave primaria compuesta evita votos duplicados)
            await conn.execute(
                text("INSERT INTO votos (usuario_id, pelicula_id, puntuacion) VALUES (:u, :p, :pts)"),
                {"u": user_id, "p": id, "pts": puntos}
            )
            return jsonify({"mensaje": "Voto registrado"}), 201
        except:
            return jsonify({"error": "Ya has votado esta pelicula"}), 400

# GET /pelicula/<id>/puntuacion: Retorna la nota media mediante función almacenada
@app.route('/pelicula/<int:id>/puntuacion', methods=['GET'])
async def ver_media(id):
    async with engine.connect() as conn:
        # Ejecuta función almacenada sp_valoracion_media
        res = await conn.execute(text("SELECT sp_valoracion_media(:pid)"), {"pid": id})
        media = res.scalar()
        
        return jsonify({"valoracion_media": float(media)}), 200

# =================================================================
# 4.4 VENTAS
# =================================================================

# GET /ventas/<anio>/<pais>: Consulta analítica con JOINs de ventas anuales por país
@app.route('/ventas/<int:anio>/<pais>', methods=['GET'])
async def reporte_ventas(anio, pais):
    # Consulta multillave: pedidos pagados unidos con clientes y películas
    query = """
        SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
        FROM pedidos ped 
        JOIN usuarios u ON ped.usuario_id = u.id 
        JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
        JOIN peliculas p ON pp.pelicula_id = p.id 
        WHERE EXTRACT(YEAR FROM ped.fecha_pago) = :anio 
          AND u.pais = :pais 
          AND ped.fecha_pago IS NOT NULL
    """
    
    async with engine.connect() as conn:
        res = await conn.execute(text(query), {"anio": anio, "pais": pais})
        
        ventas = []
        for fila in res:
            ventas.append({
                "cliente": fila.username,
                "pais": fila.pais,
                "pelicula": fila.titulo,
                "cantidad": fila.cantidad,
                "precio": float(fila.precio_unitario),
                "fecha": fila.fecha_pago.isoformat()
            })
            
        return jsonify(ventas), 200

# Arranque del microservicio principal en el puerto 5051
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)