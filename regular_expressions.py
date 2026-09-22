"""AUTLEN 2026/27 - Practica 1.

Integrantes: Jorge Palomino Rodriguez y Raul Matellano de la Morena
Completa los patrones y las sustituciones. Añade una explicacion breve de cada uno.
Pruebas: python3 -m unittest -v test_p1
"""

# Ejemplo: cadenas no vacías sobre {a,b} que empiezan por a.
RE0 = r"a[ab]*"

# 1. Cadenas binarias con un numero impar de ceros.
# Fuerza un primer 0 rodeado de 1s opcionales, seguido de cero o mas pares de 0s intercalados con 1s para mantener que sea impar.
RE1 = r"1*01*(01*01*)*"

# 2. Cadenas binarias sin dos unos consecutivos.
# Permite secuencias repetidas de 0 o 10 para evitar unos seguidos, añadiendo opcionalmente un unico 1 al final.
RE2 = r"(0|10)*(1)?"

# 3. Importes con signo opcional y parte decimal opcional de dos cifras.
# Acepta un signo opcional, un entero sin ceros a la izquierda y opcionalmente una coma seguida de dos digitos.
RE3 = r"[+-]?(0|[1-9][0-9]*)(,[0-9][0-9])?"

# 4. Archivos nombre_apellido.txt o .csv, con datos/ opcional.
# Admite el prefijo  datos/, seguido de dos bloques de letras minusculas unidos por guion bajo y terminados en .txt o .csv.
RE4 = r"(datos/)?[a-z]+_[a-z]+\.(txt|csv)"

# 5. hh:mm:ss; grupos: hora, minutos, segundos.
# Utiliza tres grupos de captura para extraer las horas, minutos y segundos.
RE5 = r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])"

# 6. rgb(r,g,b); grupos: rojo, verde, azul.
# Captura los tres valores validando rangos de 0 a 255 por longitud de cifras, evitando ceros al principio.
RE6 = r"rgb\((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9]),(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9]),(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\)"

# 7. Cada secuencia de espacios/tabuladores se sustituye por un espacio.
# Localiza secuencias de uno o mas espacios o tabuladores y los reemplaza por un unico espacio.
RE7 = r"[ \t]+"
SUB7 = r" "

# 8. Cadena completa apellido, nombre -> nombre apellido.
# Ancla el inicio y fin absoluto de la cadena para asegurar el formato estricto apellido, nombre y los reordena escribiendo primero el nombre y despues el apellido.
RE8 = r"\A([a-z]+), ([a-z]+)\Z"
SUB8 = r"\g<2> \g<1>"
