#Autores: Jorge Palomino y Raul Matellano
# Establecer los permisos de ejecución para el usuario
sudo /usr/local/bin/si2setuid.sh 3000000:100000 $USER

# Arrancar el demonio dockerd
dockerd-rootless-setuptool.sh install --skip-iptables
export DOCKER_HOST=unix:///run/user/$(id -u)/docker.sock

# Mostrar la info del demonio docker
docker info

docker compose up -d --build
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias de los tests
pip install -r p3_test_requirements.txt

# Ejecutar los tests de la P3
python3 -m pytest p3_test.py -v



#Para detener y eliminar los contenedores de esta práctica:

docker compose down


#Si al cambiar de práctica, como nos ocurrió a nosotros, surge algún error o conflicto con contenedores previos activos:

docker stop $(docker ps -q)
docker compose down -v
docker compose up -d --build

