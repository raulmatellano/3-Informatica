import os
import hashlib
import hmac
import base64
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

app = Quart(__name__)

# Configuracion basica
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:9999/si1")
SECRET_KEY = os.getenv("SECRET_KEY", "clave_super_secreta_para_la_practica")

engine = create_async_engine(DATABASE_URL, echo=False)

def hacer_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def crear_token(username):
    # Calculo la firma y la junto con el nombre de usuario
    firma = hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
    token_str = username + ":" + firma
    return base64.b64encode(token_str.encode()).decode()

def comprobar_token(cabecera):
    if not cabecera or not cabecera.startswith("Bearer "):
        return None
    try:
        # Quitamos la palabra "Bearer "
        token_b64 = cabecera.split(" ")[1]
        token_str = base64.b64decode(token_b64).decode()
        username, firma_recibida = token_str.split(":")
        
        # Comprobamos que no se ha modificado
        firma_buena = hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
        if firma_buena == firma_recibida:
            return username
    except:
        pass
    return None

@app.route('/user', methods=['PUT'])
async def registro():
    datos = await request.get_json()
    
    if not datos or 'username' not in datos or 'password' not in datos or 'pais' not in datos:
        return jsonify({"error": "Faltan datos"}), 400
        
    saldo_empiece = datos.get('saldo', 0.0)
    hash_pass = hacer_hash(datos['password'])
    
    async with engine.begin() as conn:
        # Insertamos el nuevo usuario controlando si ya existe con ON CONFLICT
        consulta = text("""
            INSERT INTO usuarios (username, password_hash, pais, saldo) 
            VALUES (:u, :p, :pais, :s) 
            ON CONFLICT (username) DO NOTHING 
            RETURNING id
        """)
        resultado = await conn.execute(consulta, {
            "u": datos['username'],
            "p": hash_pass,
            "pais": datos['pais'],
            "s": saldo_empiece
        })
        
        nuevo_id = resultado.scalar()
        
        if not nuevo_id:
            return jsonify({"error": "Ese usuario ya esta registrado"}), 409
            
        mi_token = crear_token(datos['username'])
        return jsonify({"user_id": nuevo_id, "token": mi_token}), 201

@app.route('/user/login', methods=['POST'])
async def login():
    datos = await request.get_json()
    
    if not datos or 'username' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan datos"}), 400

    async with engine.connect() as conn:
        # Buscamos el usuario
        consulta = text("SELECT id, password_hash FROM usuarios WHERE username = :u")
        resultado = await conn.execute(consulta, {"u": datos['username']})
        usuario = resultado.fetchone()
        
        if not usuario:
            return jsonify({"error": "El usuario no existe"}), 401
            
        hash_pass = hacer_hash(datos['password'])
        
        if usuario.password_hash != hash_pass:
            return jsonify({"error": "La contrasena esta mal"}), 401
            
        mi_token = crear_token(datos['username'])
        return jsonify({"user_id": usuario.id, "token": mi_token}), 200

@app.route('/user/logout', methods=['POST'])
async def logout():
    user = comprobar_token(request.headers.get("Authorization"))
    if not user:
        return jsonify({"error": "Token invalido"}), 401
        
    return jsonify({"mensaje": "Sesion cerrada"}), 200

@app.route('/user/<username>', methods=['DELETE'])
async def borrar(username):
    user = comprobar_token(request.headers.get("Authorization"))
    
    # Solo puedes borrar tu propia cuenta
    if not user or user != username:
        return jsonify({"error": "No puedes borrar esto"}), 401

    async with engine.begin() as conn:
        # Borramos el usuario directamente
        consulta = text("DELETE FROM usuarios WHERE username = :u")
        resultado = await conn.execute(consulta, {"u": username})
        
        # Si rowcount es 0, no existía nada para borrar
        if resultado.rowcount == 0:
            return jsonify({"error": "No existe"}), 404
            
        return jsonify({"mensaje": "Borrado ok"}), 200

@app.route('/user/<username>/saldo', methods=['PATCH'])
async def meter_saldo(username):
    user = comprobar_token(request.headers.get("Authorization"))
    
    if not user or user != username:
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    if not datos or 'cantidad' not in datos:
        return jsonify({"error": "Pon la cantidad"}), 400

    async with engine.begin() as conn:
        # Sumamos el saldo directamente en la BD y devolvemos el nuevo valor
        consulta = text("""
            UPDATE usuarios 
            SET saldo = saldo + :cant 
            WHERE username = :u 
            RETURNING saldo
        """)
        resultado = await conn.execute(consulta, {
            "cant": float(datos['cantidad']), 
            "u": username
        })
        fila = resultado.fetchone()
        
        if not fila:
            return jsonify({"error": "No existe"}), 404
            
        nuevo_saldo = float(fila.saldo)
        return jsonify({"saldo": nuevo_saldo}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)