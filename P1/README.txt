Práctica 1 — Microservicios. API REST en contenedor
Sistemas Informáticos. Curso 2026/2027 — EPS Universidad Autónoma de Madrid

Autores:
- [Tu Nombre y Apellidos]
Grupo: [Tu Grupo]
Equipo: [Tu Equipo]

Versión de Python: 3.11 (o superior)

## Instrucciones para ejecutar SIN Docker (con entorno virtual):

1. Activa el entorno virtual:
   source ./venv/si1p1/bin/activate

2. Define el UUID secreto (generado con uuid.uuid4()):
   export SECRET_UUID="generar-aqui-tu-uuid"

3. Inicia el microservicio de usuarios (en una terminal):
   python user.py

4. Inicia el microservicio de ficheros (en otra terminal, con el mismo entorno y UUID):
   python file.py

5. Ejecuta el script de cliente para pruebas (en una tercera terminal):
   python cliente.py

## Instrucciones para ejecutar CON Docker:

1. Crea un archivo .env en la raíz del proyecto con tu UUID:
   echo "SECRET_UUID=generar-aqui-tu-uuid" > .env

2. Construye y levanta los contenedores:
   docker-compose up --build

3. Ejecuta el cliente para pruebas:
   python cliente.py

## Puertos utilizados:
- user.py -> 5050
- file.py -> 5051
