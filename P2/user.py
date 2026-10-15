import os
import hashlib
import hmac
import base64
from quart import Quart, request, jsonify
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.future import select

app = Quart(__name__)

# Configuracion basica
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:9999/si1")
SECRET_KEY = os.getenv("SECRET_KEY", "clave_super_secreta_para_la_practica")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Modelo para SQLAlchemy ORM
class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    pais = Column(String(50), nullable=False)
    saldo = Column(Numeric(10, 2), default=0.00)

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

    async with SessionLocal() as session:
        # Miramos si ya hay alguien con ese nombre
        stmt = select(Usuario).where(Usuario.username == datos['username'])
        resultado = await session.execute(stmt)
        if resultado.scalars().first():
            return jsonify({"error": "Ese usuario ya esta registrado"}), 409
            
        nuevo_usuario = Usuario(
            username=datos['username'],
            password_hash=hacer_hash(datos['password']),
            pais=datos['pais'],
            saldo=saldo_empiece
        )
        
        session.add(nuevo_usuario)
        await session.commit()
        await session.refresh(nuevo_usuario)
        
        mi_token = crear_token(nuevo_usuario.username)
        return jsonify({"user_id": nuevo_usuario.id, "token": mi_token}), 201


@app.route('/user/login', methods=['POST'])
async def login():
    datos = await request.get_json()
    
    if not datos or 'username' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan datos"}), 400

    async with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.username == datos['username'])
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "El usuario no existe"}), 401
            
        hash_pass = hacer_hash(datos['password'])
        if usuario.password_hash != hash_pass:
            return jsonify({"error": "La contrasena esta mal"}), 401

        mi_token = crear_token(usuario.username)
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

    async with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.username == username)
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "No existe"}), 404

        await session.delete(usuario)
        await session.commit()
        return jsonify({"mensaje": "Borrado ok"}), 200


@app.route('/user/<username>/saldo', methods=['PATCH'])
async def meter_saldo(username):
    user = comprobar_token(request.headers.get("Authorization"))
    
    if not user or user != username:
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    if not datos or 'cantidad' not in datos:
        return jsonify({"error": "Pon la cantidad"}), 400

    async with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.username == username)
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "No existe"}), 404

        # Sumamos el saldo
        usuario.saldo = float(usuario.saldo) + float(datos['cantidad'])
        await session.commit()

        return jsonify({"saldo": usuario.saldo}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)