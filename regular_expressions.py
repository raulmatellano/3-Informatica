"""AUTLEN 2026/27 - Práctica 1.

Integrantes: Raúl Matellano, Jorge Palomino
Completa los patrones y las sustituciones. Añade una explicación breve de cada uno.
Pruebas: python3 -m unittest -v test_p1
"""

# Ejemplo: cadenas no vacías sobre {a,b} que empiezan por a.
RE0 = r"a[ab]*"

# 1. Número impar de ceros.
RE1 = r"1*01*(?:01*01*)*"

# 2. Sin dos unos consecutivos; se admite la cadena vacía.
RE2 = r"(0|10)*1"

# 3. Importes con signo opcional y parte decimal opcional de dos cifras.
# Explicación: Signo opcional, luego o un cero solo o un número del 1 al 9 seguido de lo que sea. Al final la coma y dos dígitos todo opcional.
RE3 = r"[+-]?(?:0|[1-9][0-9]*)(?:,[0-9]{2})?"

# 4. Archivos nombre_apellido.txt o .csv, con datos/ opcional.
# Explicación: Hago opcional la carpeta datos, exijo letras y un guion bajo, y termino con el punto escapado y las dos opciones de extensión.
RE4 = r"(?:datos/)?[a-z]+_[a-z]+\.(?:txt|csv)"

# 5. hh:mm:ss; grupos: hora, minutos, segundos.
# Explicación: Divido las horas en dos bloques (hasta el 19, y del 20 al 23). Minutos y segundos van del 0 al 5 limitando el primer número.
RE5 = r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])"

# 6. rgb(r,g,b); grupos: rojo, verde, azul.
# Explicación: Como no se admiten ceros a la izquierda, divido el rango 0-255 en 5 trozos lógicos para cada uno de los colores.
RE6 = r"rgb\(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]),([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\)"

# 7. Cada secuencia de espacios/tabuladores se sustituye por un espacio.
# Explicación: Busco uno o más espacios o tabuladores juntos y en la sustitución pongo un único espacio normal.
RE7 = r"[ \t]+"
SUB7 = r" "

# 8. Cadena completa apellido, nombre -> nombre apellido.
# Explicación: Anclo la búsqueda al inicio y al final de la cadena para que no edite a medias, capturo los dos nombres y los pego al revés.
RE8 = r"\A([a-z]+), ([a-z]+)\Z"
SUB8 = r"\g<2> \g<1>"