import os
import hashlib
import hmac
import base64
from datetime import datetime
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

app = Quart(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:9999/si1")
SECRET_KEY = os.getenv("SECRET_KEY", "clave")

engine = create_async_engine(DATABASE_URL, echo=False)

# Comprueba que el token Bearer sea valido y saca el usuario
def comprobar_token(cabecera):
    if not cabecera or not cabecera.startswith("Bearer "):
        return None
    try:
        token_b64 = cabecera.split(" ")[1]
        token_str = base64.b64decode(token_b64).decode()
        username, firma_recibida = token_str.split(":")
        
        firma_buena = hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
        if firma_buena == firma_recibida:
            return username
    except:
        pass
    return None

# Añade una pelicula nueva a la base de datos
@app.route('/pelicula', methods=['PUT'])
async def nueva_peli():
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    datos = await request.get_json()
    
    async with engine.begin() as conn:
        consulta = text("""
            INSERT INTO peliculas (titulo, director_id, anio, precio, stock) 
            VALUES (:t, :d, :a, :p, :s) RETURNING id
        """)
        resultado = await conn.execute(consulta, {
            "t": datos['titulo'],
            "d": datos['director_id'],
            "a": datos['anio'],
            "p": datos['precio'],
            "s": datos['stock']
        })
        nuevo_id = resultado.scalar()
        return jsonify({"pelicula_id": nuevo_id}), 201

# Borra una pelicula por su id
@app.route('/pelicula/<int:id>', methods=['DELETE'])
async def quitar_peli(id):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM peliculas WHERE id = :id"), {"id": id})
        return jsonify({"mensaje": "Borrada"}), 200

# Busca peliculas filtrando por director o año
@app.route('/peliculas', methods=['GET'])
async def buscador():
    dir_id = request.args.get('director_id')
    anio = request.args.get('anio')
    
    async with engine.connect() as conn:
        sql = """
            SELECT p.id, p.titulo, d.nombre AS director, p.anio, p.precio, p.stock,
                   STRING_AGG(a.nombre, ', ') AS actores
            FROM peliculas p
            JOIN directores d ON p.director_id = d.id
            LEFT JOIN pelicula_actores pa ON p.id = pa.pelicula_id
            LEFT JOIN actores a ON pa.actor_id = a.id
            WHERE 1=1
        """
        parametros = {}
        
        if dir_id:
            sql += " AND p.director_id = :dir"
            parametros['dir'] = int(dir_id)
        if anio:
            sql += " AND p.anio = :anio"
            parametros['anio'] = int(anio)
            
        sql += " GROUP BY p.id, p.titulo, d.nombre, p.anio, p.precio, p.stock"
        
        resultado = await conn.execute(text(sql), parametros)
        lista = []
        for f in resultado:
            lista.append({
                "id": f.id,
                "titulo": f.titulo,
                "director": f.director,
                "actores": f.actores if f.actores else "",
                "anio": f.anio,
                "precio": float(f.precio),
                "stock": f.stock
            })
            
        return jsonify(lista), 200

# Mete una pelicula al carrito (si no hay pedido abierto, crea uno)
@app.route('/carrito/<int:user_id>', methods=['POST'])
async def meter_carrito(user_id):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    datos = await request.get_json()
    id_peli = datos['pelicula_id']
    cant = datos.get('cantidad', 1)
    
    async with engine.begin() as conn:
        sql = text("""
            WITH carrito_abierto AS (
                SELECT id FROM pedidos 
                WHERE usuario_id = :u AND fecha_pago IS NULL
            ),
            carrito_nuevo AS (
                INSERT INTO pedidos (usuario_id) 
                SELECT :u WHERE NOT EXISTS (SELECT 1 FROM carrito_abierto)
                RETURNING id
            ),
            carrito_final AS (
                SELECT id FROM carrito_abierto 
                UNION ALL 
                SELECT id FROM carrito_nuevo
            ),
            peli_precio AS (
                SELECT precio FROM peliculas WHERE id = :p
            )
            INSERT INTO pedido_peliculas (pedido_id, pelicula_id, cantidad, precio_unitario)
            SELECT c.id, :p, :c, peli.precio
            FROM carrito_final c, peli_precio peli
        """)
        
        await conn.execute(sql, {"u": user_id, "p": id_peli, "c": cant})
        return jsonify({"mensaje": "Peli metida al carrito"}), 201

# Saca una pelicula del carrito del usuario
@app.route('/carrito/<int:user_id>/<int:id_peli>', methods=['DELETE'])
async def quitar_del_carrito(user_id, id_peli):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    async with engine.begin() as conn:
        sql = text("""
            DELETE FROM pedido_peliculas 
            WHERE pelicula_id = :p 
            AND pedido_id = (
                SELECT id FROM pedidos 
                WHERE usuario_id = :u AND fecha_pago IS NULL
            )
        """)
        
        resultado = await conn.execute(sql, {"u": user_id, "p": id_peli})
        
        if resultado.rowcount == 0:
            return jsonify({"error": "No tienes esta peli en el carrito o no hay carrito"}), 404
            
        return jsonify({"mensaje": "Peli quitada del carrito"}), 200

# Paga el carrito del usuario usando el procedimiento de la BD
@app.route('/carrito/<int:user_id>/pagar', methods=['POST'])
async def pagar_pedido(user_id):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    async with engine.begin() as conn:
        try:
            await conn.execute(text("SELECT sp_pagar_carrito(:u)"), {"u": user_id})
            return jsonify({"mensaje": "Pagado ok"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 402

# Devuelve los pedidos que ha hecho el usuario
@app.route('/pedidos/<int:user_id>', methods=['GET'])
async def ver_mis_pedidos(user_id):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT id, fecha_pago, total FROM pedidos WHERE usuario_id = :u"), 
            {"u": user_id}
        )
        lista = []
        for f in res:
            lista.append({
                "pedido_id": f.id,
                "fecha_pago": str(f.fecha_pago) if f.fecha_pago else None,
                "total": float(f.total)
            })
        return jsonify(lista), 200

# Guarda el voto de un usuario a una pelicula (de 0 a 10)
@app.route('/pelicula/<int:id>/voto', methods=['POST'])
async def votar(id):
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "No autorizado"}), 401
        
    datos = await request.get_json()
    puntos = datos['puntuacion']
    
    if puntos < 0 or puntos > 10:
        return jsonify({"error": "Nota mala"}), 400
        
    async with engine.begin() as conn:
        try:
            sql = text("""
                INSERT INTO votos (usuario_id, pelicula_id, puntuacion) 
                SELECT id, :p, :pts FROM usuarios WHERE username = :u
            """)
            await conn.execute(sql, {"u": user, "p": id, "pts": puntos})
            return jsonify({"mensaje": "Votado"}), 201
        except:
            return jsonify({"error": "Ya votaste esto"}), 400

# Pide a la BD la nota media de la pelicula
@app.route('/pelicula/<int:id>/puntuacion', methods=['GET'])
async def nota_media(id):
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT sp_valoracion_media(:p)"), {"p": id})
        media = res.scalar()
        return jsonify({"valoracion_media": float(media)}), 200

# Saca el listado de ventas filtrado por año y por pais
@app.route('/ventas/<int:anio>/<pais>', methods=['GET'])
async def reporte_ventas(anio, pais):
    query = """
        SELECT u.username, u.pais, p.titulo, pp.cantidad, pp.precio_unitario, ped.fecha_pago 
        FROM pedidos ped 
        JOIN usuarios u ON ped.usuario_id = u.id 
        JOIN pedido_peliculas pp ON ped.id = pp.pedido_id 
        JOIN peliculas p ON pp.pelicula_id = p.id 
        WHERE ped.fecha_pago >= :inicio 
          AND ped.fecha_pago < :fin
          AND u.pais = :pais 
    """
    
    inicio_anio = datetime(anio, 1, 1)
    fin_anio = datetime(anio + 1, 1, 1)
    
    async with engine.connect() as conn:
        res = await conn.execute(text(query), {"inicio": inicio_anio, "fin": fin_anio, "pais": pais})
        ventas = []
        for f in res:
            ventas.append({
                "cliente": f.username,
                "pais": f.pais,
                "pelicula": f.titulo,
                "cantidad": f.cantidad,
                "precio": float(f.precio_unitario),
                "fecha": str(f.fecha_pago)
            })
        return jsonify(ventas), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
