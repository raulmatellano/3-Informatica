'''
    ethmsg.py
    Implementación del protocolo de mensajería básica para emisión de mensajes en tiempo real sobre Ethernet.
    Autor: Jorge Palomino y Raul Matellano
    2024 EPS-UAM
'''

# ==============================================================================
# RESUMEN GENERAL Y GUÍA DE ESTUDIO: ethmsg.py (PROTOCOLO DE MENSAJERÍA SOBRE ETHERNET)
# ==============================================================================
# Este módulo implementa un protocolo sencillo de mensajería que viaja directamente
# sobre tramas Ethernet de Nivel 2, SIN utilizar cabeceras de red ni transporte (sin IP, UDP ni TCP).
#
# CARACTERÍSTICAS PRINCIPALES:
#   1. Ethertype oficial: 0x0AA0 (asignado específicamente en el enunciado de la práctica).
#   2. Destino: Difusión (Broadcast = FF:FF:FF:FF:FF:FF). Todos los equipos de la LAN
#      que tengan arrancado el programa recibirán y mostrarán los mensajes en su pantalla.
#   3. Estructura del Payload EthMsg (lo que va DENTRO del campo de datos de Ethernet):
#      ┌─────────────────────────────────┬───────────────────────────────────────┐
#      │ Longitud del mensaje (2 Bytes)  │ Contenido del mensaje en texto UTF-8  │
#      │ Formato: '!H' (unsigned short)  │ Longitud variable (según campo prev.) │
#      │ Bytes [0:2] en orden de red     │ Bytes [2 : 2 + longitud]              │
#      └─────────────────────────────────┴───────────────────────────────────────┘
#
# ------------------------------------------------------------------------------
# FLUJO DE TRABAJO (QUIÉN LLAMA A QUIÉN):
# ------------------------------------------------------------------------------
# [INICIALIZACIÓN]:
#   practica2.py
#       └──> initEthMsg(interface)
#               └──> registerEthCallback(process_ethMsg_frame, 0x0AA0) [en ethernet.py]
#
# [ENVÍO DE MENSAJE (COMANDO 'm')]:
#   practica2.py (usuario escribe "m Hola mundo")
#       └──> sendEthMsg("Hola mundo")
#               ├──> Codifica texto a bytes UTF-8 y empaqueta longitud (2B, '!H')
#               ├──> Concatena payload: [longitud(2B)] + [texto codificado]
#               └──> sendEthernetFrame(trama, len(trama), 0x0AA0, broadcast) [en ethernet.py]
#
# [RECEPCIÓN DE MENSAJE]:
#   rxThread ──> process_frame ──> process_Ethernet_frame [en ethernet.py]
#       └──> detecta Ethertype 0x0AA0
#               └──> process_ethMsg_frame(us, header, payload, srcMac)
#                       ├──> Desempaqueta longitud de data[0:2] con '!H'
#                       ├──> Decodifica texto de data[2:2+longitud] con decode('utf-8')
#                       ├──> Formatea MAC origen a "XX:XX:XX:XX:XX:XX"
#                       ├──> Extrae timestamp (header.ts.tv_sec y tv_usec) y convierte a fecha
#                       └──> Imprime por pantalla: [fecha.microsegundos] MAC (N bytes) : mensaje
# ==============================================================================

from ethernet import *   # Importa sendEthernetFrame, registerEthCallback, etc.
import logging
import socket
import struct
import fcntl
import time
from threading import Lock
from expiringdict import ExpiringDict   
import datetime

# ------------------------------------------------------------------------------
# CONSTANTES GLOBALES
# ------------------------------------------------------------------------------

# Ethertype oficial del protocolo EthMsg según enunciado de la práctica: 0x0AA0.
# Al registrarlo en Ethernet, toda trama entrante con tipo 0x0AA0 se deriva a process_ethMsg_frame.
ETHTYPE = 0x0AA0

# Dirección MAC de difusión (Broadcast): FF:FF:FF:FF:FF:FF (6 bytes a 0xFF).
# EthMsg siempre emite en broadcast para que llegue a todos los puestos de la LAN.
broadcast = bytes([0xFF]*6)


def process_ethMsg_frame(us:ctypes.c_void_p,header:pcap_pkthdr,data:bytes,srcMac:bytes) -> None:
    '''
        Nombre: process_EthMsg_frame
        Descripción: Esta función procesa las tramas mensajes sobre ethernet. 
            Se ejecutará por cada trama Ethenet que se reciba con Ethertype ETHTYPE (si ha sido registrada en initEth). 
                - Imprimir el contenido de los datos indicando la direccion MAC del remitente así como el tiempo de recepcion del mensaje, según el siguiente formato:
					[<segundos.microsegundos>] <MAC>: <mensaje> 
                - En caso de que no exista retornar
            
        Argumentos:
            -us: Datos de usuario pasados desde la llamada de pcap_loop. En nuestro caso será None
            -header: cabecera pcap_pktheader
            -data: array de bytes con el contenido de la trama ethMsg. Los dos primeros bytes tienen la longitud del mensaje en orden de red. El resto de bytes son el mensaje en sí mismo.
            -srcMac: MAC origen de la trama Ethernet que se ha recibido
        Retorno: Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - process_Ethernet_frame() en ethernet.py (al recibir una trama con Ethertype 0x0AA0).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - No llama a funciones de red; procesa la información y la imprime por consola con print().
    #
    # PARÁMETROS:
    #   - us (ctypes.c_void_p): Datos de usuario de pcap_loop (siempre None en nuestra práctica).
    #   - header (pcap_pkthdr): Metadatos de captura provistos por libpcap:
    #       * header.ts.tv_sec: Segundos Unix epoch desde el 1 de enero de 1970.
    #       * header.ts.tv_usec: Fracción de microsegundos de la marca temporal (0 a 999999).
    #   - data (bytes): Payload de EthMsg (excluye la cabecera Ethernet de 14 bytes):
    #       * data[0:2]: Longitud del mensaje (entero de 16 bits en orden de red / big-endian).
    #       * data[2:2+longitud]: Bytes con el texto del mensaje codificado en UTF-8.
    #   - srcMac (bytes): 6 bytes con la dirección MAC física del equipo emisor.
    #
    # RETORNO:
    #   - None.
    #
    # FORMATO EXACTO EXIGIDO POR EL ENUNCIADO:
    #   [AAAA/MM/DD HH:MM:SS.uuuuuu] XX:XX:XX:XX:XX:XX (N bytes) : <mensaje>
    #   Ejemplo: [2026/10/12 16:12:27.123456] 00:27:51:A3:B8:9E (48 bytes) : Hola mundo
    # ==========================================================================
    
    # 1. Extraemos la longitud del mensaje: primeros 2 bytes desempaquetados con '!H'
    # ('!' = network byte order / big-endian, 'H' = unsigned short de 2 bytes)
    longitud = struct.unpack('!H', data[0:2])[0]
    
    # 2. Extraemos el mensaje de texto: desde el byte 2 hasta (2 + longitud) y decodificamos UTF-8
    mensaje = data[2:2+longitud].decode('utf-8')    
    
    # 3. Convertimos la MAC origen de 6 bytes a cadena legible en formato hexadecimal "XX:XX:XX:XX:XX:XX"
    partes_mac = []
    for b in srcMac:
        byte_hexadecimal = '{:02X}'.format(b)  # 2 dígitos hex en mayúsculas con cero a la izquierda si hace falta      
        partes_mac.append(byte_hexadecimal)
    mac = ':'.join(partes_mac)    
    
    # 4. Extraemos el timestamp de recepción de la cabecera pcap (segundos y microsegundos)
    segundos = header.ts.tv_sec
    microsegundos = header.ts.tv_usec
    
    # 5. Formateamos la fecha y hora legible (Año/Mes/Día Hora:Minuto:Segundo)
    fecha_hora = datetime.datetime.fromtimestamp(segundos).strftime('%Y/%m/%d %H:%M:%S')
    
    # 6. Imprimimos el mensaje por pantalla cumpliendo el formato oficial del enunciado
    # ({microsegundos:06d} fuerza 6 dígitos rellenando con ceros si microsegundos < 100000)
    print(f"[{fecha_hora}.{microsegundos:06d}] {mac} ({longitud} bytes) : {mensaje}")



def initEthMsg(interface:str) -> int:
    '''
        Nombre: initEthMsg
        Descripción: Esta función construirá inicializará el nivel ethMsg. Esta función debe realizar, al menos, las siguientes tareas:
            -Registrar la función del callback process_ethMsg_frame con el Ethertype ETHTYPE
        Argumentos:   
			interfaz
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py en el arranque del sistema (PASO 2 del orden de inicialización).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - registerEthCallback(process_ethMsg_frame, ETHTYPE) en ethernet.py.
    #
    # PARÁMETROS:
    #   - interface (str): Nombre de la interfaz de red (ej: "eth0", "h1-eth0").
    #
    # RETORNO:
    #   - 0: Nivel EthMsg inicializado y callback registrado correctamente.
    # ==========================================================================
    # Registramos el callback para el Ethertype oficial 0x0AA0. A partir de este momento,
    # cualquier trama Ethernet con tipo 0x0AA0 será enviada a process_ethMsg_frame.
    registerEthCallback(process_ethMsg_frame, ETHTYPE)  
    return 0


def sendEthMsg(message:bytes) -> bytes:
    '''
        Nombre: sendEthMsg
        Descripción: Esta función mandara un mensaje en broacast 
            
            Esta función debe realizar, al menos, las siguientes tareas:
                - Crear una trama Ehernet con el mensaje remitido. Los datos de la trama tienen que incluir la longitud del mensaje en orden de red, seguido del mensaje.
                - Enviar un mensaje en broadcast. La llamada a Ethernet debe tener en cuenta la longitud total (longitud+mensaje)
		Argumentos:
			message: datos con el mensaje a remitir.
                
        Retorno: 
			Numero de Bytes transmitidos en el mensaje.
			None en caso de que no haya podido emitir el mensaje
                
          
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py cuando el usuario teclea el comando 'm <texto>'.
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - sendEthernetFrame(trama, len(trama), ETHTYPE, broadcast) en ethernet.py.
    #
    # PARÁMETROS:
    #   - message (str): Cadena de texto introducida por el usuario a enviar por la LAN.
    #
    # RETORNO:
    #   - int: Número total de bytes del payload transmitido (2 bytes de cabecera + longitud mensaje).
    #
    # FUNCIONAMIENTO INTERNO PASO A PASO:
    #   1. Codifica el texto string a bytes UTF-8.
    #   2. Calcula la longitud en bytes del mensaje.
    #   3. Empaqueta la longitud en 2 bytes en orden de red big-endian con '!H'.
    #   4. Concatena los 2 bytes de longitud + los bytes del texto.
    #   5. Invoca a sendEthernetFrame con ethertype 0x0AA0 y dirección broadcast FF:FF:FF:FF:FF:FF.
    # ==========================================================================
    global broadcast            
    
    # 1. Codificamos el mensaje de texto a bytes en formato UTF-8
    mensaje = message.encode('utf-8')
    
    # 2. Obtenemos el número de bytes reales que ocupa el mensaje codificado
    longitud = len(mensaje)
    
    # 3. Empaquetamos la longitud en 2 bytes big-endian (orden de red '!H')
    longitud_bytes = struct.pack('!H', longitud) 
    
    # 4. Construimos el payload de EthMsg: [longitud (2B)] + [texto (NB)]
    trama = longitud_bytes + mensaje
    
    # 5. Enviamos la trama a nivel Ethernet:
    #    - Datos: payload EthMsg (longitud + texto)
    #    - Longitud: total de bytes del payload
    #    - Ethertype: 0x0AA0 (protocolo EthMsg)
    #    - Destino: broadcast (FF:FF:FF:FF:FF:FF)
    sendEthernetFrame(trama, len(trama), ETHTYPE, broadcast)
    
    # 6. Devolvemos el total de bytes transmitidos en el nivel de aplicación
    return len(trama)
