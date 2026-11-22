# Definimos la imagen base de python
FROM python:3.12

# Establecemos el directorio de trabajo del contenedor
WORKDIR /app

# Copia el archivo de dependencias para instalar las librerias necesarias de python
COPY requirements.txt requirements.txt

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la API dentro del contenedor
COPY . .

# Abre el puerto de escucha de auth-service
EXPOSE 5050

# Arranca el servidor Hypercorn con recarga automática
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:5050", "--reload"]