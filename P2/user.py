"""
Microservicio de gestión de usuarios (Puerto 5050).
Implementado con Quart y SQLAlchemy ORM (modo asíncrono).
"""
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

# Configuración de base de datos y clave secreta para firma de tokens
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://alumnodb:1234@localhost:9999/si1")
SECRET_KEY = os.getenv("SECRET_KEY", "clave_super_secreta_para_la_practica")

# Motor y sesión asíncrona para SQLAlchemy ORM
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Modelo ORM para la tabla 'usuarios'
class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    pais = Column(String(50), nullable=False)
    saldo = Column(Numeric(10, 2), default=0.00)

# Genera hash SHA-256 para almacenar la contraseña de forma segura
def generar_hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Genera token stateless en base64: "username:firma_hmac"
def generar_token(username):
    firma = hmac.new(SECRET_KEY.encode(), username.encode(), hashlib.sha256).hexdigest()
    token_raw = f"{username}:{firma}"
    token = base64.b64encode(token_raw.encode()).decode()
    return token

# Valida cabecera 'Authorization: Bearer <token>' verificando la firma HMAC
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

# PUT /user: Registra un nuevo usuario con hash de contraseña y devuelve token
@app.route('/user', methods=['PUT'])
async def registrar_usuario():
    datos = await request.get_json()
    
    # Validación de campos obligatorios
    if not datos or 'username' not in datos or 'password' not in datos or 'pais' not in datos:
        return jsonify({"error": "Faltan datos obligatorios"}), 400
        
    saldo_inicial = datos.get('saldo', 0.00)

    async with SessionLocal() as session:
        # Comprobar si el usuario ya existe
        stmt = select(Usuario).where(Usuario.username == datos['username'])
        resultado = await session.execute(stmt)
        user_existente = resultado.scalars().first()
        
        if user_existente:
            return jsonify({"error": "El nombre de usuario ya esta en uso"}), 409
            
        # Crear y persistir nuevo usuario
        nuevo_user = Usuario(
            username=datos['username'],
            password_hash=generar_hash_password(datos['password']),
            pais=datos['pais'],
            saldo=saldo_inicial
        )
        
        session.add(nuevo_user)
        await session.commit()
        await session.refresh(nuevo_user)
        
        token = generar_token(nuevo_user.username)
        return jsonify({"user_id": nuevo_user.id, "token": token}), 201

# POST /user/login: Comprueba credenciales y emite token si coinciden
@app.route('/user/login', methods=['POST'])
async def login():
    datos = await request.get_json()
    
    if not datos or 'username' not in datos or 'password' not in datos:
        return jsonify({"error": "Faltan datos"}), 400

    async with SessionLocal() as session:
        # Buscar usuario por username
        stmt = select(Usuario).where(Usuario.username == datos['username'])
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 401
            
        # Comparar hash de contraseña
        hash_pass = generar_hash_password(datos['password'])
        if usuario.password_hash != hash_pass:
            return jsonify({"error": "Contrasena incorrecta"}), 401

        token = generar_token(usuario.username)
        return jsonify({"user_id": usuario.id, "token": token}), 200

# POST /user/logout: Valida el token del usuario para confirmar cierre de sesión
@app.route('/user/logout', methods=['POST'])
async def logout():
    usuario_autenticado = verificar_token(request.headers.get("Authorization"))
    
    if not usuario_autenticado:
        return jsonify({"error": "No autorizado o token invalido"}), 401
        
    return jsonify({"mensaje": "Sesion cerrada correctamente"}), 200

# DELETE /user/<username>: Borra un usuario (solo si el token coincide con la cuenta)
@app.route('/user/<username>', methods=['DELETE'])
async def borrar_usuario(username):
    usuario_autenticado = verificar_token(request.headers.get("Authorization"))
    
    # Comprobar que quien borra es el propio usuario
    if not usuario_autenticado or usuario_autenticado != username:
        return jsonify({"error": "No tienes permiso para borrar este usuario"}), 401

    async with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.username == username)
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        await session.delete(usuario)
        await session.commit()
        
        return jsonify({"mensaje": "Usuario borrado con exito"}), 200

# PATCH /user/<username>/saldo: Modifica el saldo del usuario autenticado
@app.route('/user/<username>/saldo', methods=['PATCH'])
async def actualizar_saldo(username):
    usuario_autenticado = verificar_token(request.headers.get("Authorization"))
    
    if not usuario_autenticado or usuario_autenticado != username:
        return jsonify({"error": "No autorizado"}), 401

    datos = await request.get_json()
    if not datos or 'cantidad' not in datos:
        return jsonify({"error": "Debes indicar la cantidad a ingresar"}), 400

    async with SessionLocal() as session:
        stmt = select(Usuario).where(Usuario.username == username)
        resultado = await session.execute(stmt)
        usuario = resultado.scalars().first()

        if not usuario:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Incrementar o decrementar saldo
        nueva_cantidad = float(datos['cantidad'])
        usuario.saldo = float(usuario.saldo) + nueva_cantidad
        
        await session.commit()
        return jsonify({"saldo": usuario.saldo}), 200

# Arranque del microservicio en el puerto 5050
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)