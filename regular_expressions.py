"""AUTLEN 2026/27 - Práctica 1.

Integrantes: Jorge Palomino Rodriguez y Raul Matellano de la Morena
Completa los patrones y las sustituciones. Añade una explicación breve de cada uno.
Pruebas: python3 -m unittest -v test_p1
"""

# Ejemplo: cadenas no vacías sobre {a,b} que empiezan por a.
RE0 = r"a[ab]*"

# 1. Cadenas binarias con un número impar de ceros.
# Un cero obligatorio (rodeado de unos) seguido de parejas de ceros (cada una rodeada de unos).
RE1 = r"1*01*(01*01*)*"

# 2. Cadenas binarias sin dos unos consecutivos.
# Bloques de ceros sueltos o 10 repetidos, permitiendo opcionalmente un 1 al final.
RE2 = r"(0|10)*(1)?"

# 3. Importes con signo opcional y parte decimal opcional de dos cifras.
# Signo opcional [+-]?, entero (0 o cifra 1-9 seguida de dígitos), y decimal opcional (, seguido de dos dígitos).
RE3 = r"[+-]?(0|[1-9][0-9]*)(,[0-9][0-9])?"

# 4. Archivos nombre_apellido.txt o .csv, con datos/ opcional.
# Directorio opcional datos/, letras minúsculas separadas por un guion bajo, y extensión .txt o .csv.
RE4 = r"(datos/)?[a-z]+_[a-z]+\.(txt|csv)"

# 5. hh:mm:ss; grupos: hora, minutos, segundos.
# Captura exactamente 3 grupos: horas 00-23, minutos 00-59 y segundos 00-59.
RE5 = r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])"

# 6. rgb(r,g,b); grupos: rojo, verde, azul.
# Rango 0-255 sin ceros iniciales: 250-255, 200-249, 100-199, 10-99 o 0-9.
RE6 = r"rgb\((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9]),(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9]),(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\)"
# 7. Cada secuencia de espacios/tabuladores se sustituye por un espacio.
# Detecta 1 o más espacios/tabuladores y los sustituye por un único espacio.
RE7 = r"[ \t]+"
SUB7 = r" "

# 8. Cadena completa apellido, nombre -> nombre apellido.
# Captura apellido y nombre si la cadena completa cumple exactamente el formato, y los invierte.
RE8 = r"\A([a-z]+), ([a-z]+)\Z"
SUB8 = r"\g<2> \g<1>"