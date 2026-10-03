
Autores:
Jorge Palomino y Raul Matellano

## Instrucciones para ejecutar con Docker (Recomendado):

1. Construye y levanta los contenedores en segundo plano:
   sudo docker-compose up --build -d

2. Ejecuta el cliente automático de pruebas para verificar el funcionamiento (19/19 tests):
   python cliente.py

3. Para detener los contenedores al terminar:
   sudo docker-compose down

## Instrucciones para ejecutar en local (sin Docker):

1. Activa el entorno virtual:
   source ./venv/silp1/bin/activate

2. Inicia el microservicio de usuarios (en una terminal):
   python user.py

3. Inicia el microservicio de ficheros (en una segunda terminal):
   python file.py

4. Ejecuta el cliente de pruebas (en una tercera terminal):
   python cliente.py

## Puertos utilizados:
- user.py -> Puerto 5050
- file.py -> Puerto 5051
