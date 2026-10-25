'''
    arp.py
    Implementación del protocolo ARP y funciones auxiliares que permiten realizar resoluciones de direcciones IP.
    Autor: Jorge Palomino y Raul Matellano
    2019 EPS-UAM
'''

# ==============================================================================
# RESUMEN GENERAL Y GUÍA DE ESTUDIO: arp.py (NIVEL DE RESOLUCIÓN DE DIRECCIONES)
# ==============================================================================
# Este módulo implementa el protocolo ARP (Address Resolution Protocol - RFC 826).
#
# OBJETIVO PRINCIPAL:
#   Dada una dirección de red IPv4 (entero de 32 bits, ej: 10.0.0.1), averiguar cuál
#   es la dirección física MAC (6 bytes, ej: 00:00:00:00:00:02) del equipo que posee
#   dicha IP en la red de área local (LAN).
#
# ------------------------------------------------------------------------------
# ESTRUCTURA DETALLADA DEL PAQUETE ARP (28 BYTES EN TOTAL):
# ------------------------------------------------------------------------------
# Se transporta como PAYLOAD dentro de la trama Ethernet (tras los 14B de cabecera Ethernet):
#
#   Byte  0 - 1 : Hardware Type (2B)  ──> 0x0001 (Ethernet)
#   Byte  2 - 3 : Protocol Type (2B)  ──> 0x0800 (IPv4)
#   Byte    4   : Hardware Size (1B)  ──> 0x06 (Tamaño de dirección MAC: 6 bytes)
#   Byte    5   : Protocol Size (1B)  ──> 0x04 (Tamaño de dirección IPv4: 4 bytes)
#   ─────────────────────────────────────────────────────────────────────────────
#   ==> Bytes [0:6] = ARPHeader fija común: bytes([0x00,0x01,0x08,0x00,0x06,0x04])
#   ─────────────────────────────────────────────────────────────────────────────
#   Byte  6 - 7 : Opcode (2B)         ──> 0x0001 = Request (Petición)
#                                         0x0002 = Reply (Respuesta)
#   Byte  8 - 13: Sender MAC (6B)     ──> Dirección MAC de quien envía el ARP
#   Byte 14 - 17: Sender IP (4B)      ──> Dirección IP de quien envía el ARP
#   Byte 18 - 23: Target MAC (6B)     ──> Dirección MAC del equipo buscado:
#                                         * En Request: 00:00:00:00:00:00 (desconocida)
#                                         * En Reply:   MAC de quien preguntó
#   Byte 24 - 27: Target IP (4B)      ──> Dirección IP del equipo buscado:
#                                         * En Request: IP que queremos resolver
#                                         * En Reply:   IP de quien preguntó
#
# ------------------------------------------------------------------------------
# CONCURRENCIA, HILOS Y SINCRONIZACIÓN (¡PREGUNTA ESTRELLA DEL EXAMEN!):
# ------------------------------------------------------------------------------
# En este programa conviven 2 hilos interactuando sobre variables compartidas:
#   - HILO 1 (Hilo Principal / ARPResolution):
#       Llamado por la consola cuando escribes 'a <IP>'. Configura las variables globales
#       y entra en un bucle durmiendo en intervalos de 0.1s esperando la respuesta.
#   - HILO 2 (Hilo de Recepción / processARPReply):
#       Lanzado por process_frame cuando llega una trama desde la red. Recibe la respuesta,
#       la valida, copia la MAC y cambia la bandera awaitingResponse a False.
#
# VARIABLES COMPARTIDAS (protegidas mediante globalLock):
#   - requestedIP (int):      La IP por la que estamos preguntando actualmente.
#   - resolvedMAC (bytes):    La MAC resuelta que el hilo receptor entrega a ARPResolution.
#   - awaitingResponse (bool): True mientras esperamos; False cuando llega la respuesta.
#
# PROTECCIÓN DE LA CACHÉ (protegida mediante cacheLock):
#   - cache: Diccionario de tipo ExpiringDict(max_len=100, max_age_seconds=10).
#     Asocia IP (int) ──> MAC (bytes). Las entradas caducan solas a los 10 segundos.
#
# ------------------------------------------------------------------------------
# FLUJO DE TRABAJO (QUIÉN LLAMA A QUIÉN):
# ------------------------------------------------------------------------------
# [ARRANQUE]:
#   practica2.py ──> initARP(interface)
#                       ├──> registerEthCallback(process_arp_frame, 0x0806)
#                       ├──> getIP(interface) [guarda myIP]
#                       ├──> getHwAddr(interface) [guarda myMAC]
#                       └──> ARPResolution(myIP) [ARP Gratuito: si != None ──> error IP duplicada]
#
# [SOLICITAR RESOLUCIÓN (COMANDO 'a <IP>')]:
#   practica2.py ──> ARPResolution(ip)
#                       ├── 1. ¿Está en caché? ──> Sí: devuelve MAC sin emitir tramas
#                       ├── 2. No: Prepara requestedIP, awaitingResponse=True con globalLock
#                       ├── 3. peticion = createARPRequest(ip)
#                       └── 4. Bucle reintentos (hasta 3 veces, 1 segundo cada intento):
#                               ├──> sendEthernetFrame(peticion, len, 0x0806, broadcastAddr)
#                               └──> while espera < 1.0s:
#                                       └──> ¿awaitingResponse == False? ──> return resolvedMAC
#
# [RECEPCIÓN DE TRAMA ARP]:
#   ethernet.py ──> process_arp_frame(us, header, data, srcMac)
#                       ├──> Comprueba: len(data) >= 28 y data[0:6] == ARPHeader
#                       ├──> Lee Opcode (data[6:8])
#                       ├── Si Opcode == 1 ──> processARPRequest(data, srcMac)
#                       │                           ├──> ¿target_ip == myIP?
#                       │                           ├──> ¿Anti-spoofing? sender_mac == srcMac
#                       │                           ├──> resp = createARPReply(sender_ip, sender_mac)
#                       │                           └──> sendEthernetFrame(resp, len, 0x0806, sender_mac)
#                       └── Si Opcode == 2 ──> processARPReply(data, srcMac)
#                                                   ├──> ¿target_ip == myIP y sender_mac == srcMac?
#                                                   ├──> with globalLock:
#                                                   │       ├──> ¿sender_ip == requestedIP?
#                                                   │       ├──> resolvedMAC = sender_mac
#                                                   │       ├──> with cacheLock: cache[sender_ip] = sender_mac
#                                                   │       └──> awaitingResponse = False (¡despierta al hilo 1!)
# ==============================================================================

from ethernet import *   # Importa sendEthernetFrame, registerEthCallback, getHwAddr, broadcastAddr, etc.
import logging
import socket
import struct
import fcntl
import time
from threading import Lock
from expiringdict import ExpiringDict

# ------------------------------------------------------------------------------
# VARIABLES GLOBALES Y SEMÁFOROS
# ------------------------------------------------------------------------------

# Semáforo global: protege las variables de sincronización entre hilos
# (requestedIP, awaitingResponse, resolvedMAC) para evitar condiciones de carrera.
globalLock = Lock()

# Dirección MAC de difusión (Broadcast): FF:FF:FF:FF:FF:FF
broadcastAddr = bytes([0xFF]*6)

# Cabecera ARP común para la combinación Ethernet (HW=0x0001, len=6) e IPv4 (Proto=0x0800, len=4)
ARPHeader = bytes([0x00,0x01,0x08,0x00,0x06,0x04])

# Longitud en bytes de la cabecera común de ARP
ARP_HLEN = 6

# Variable que almacena la dirección IP (int de 32 bits) que se está intentando resolver actualmente
requestedIP = None

# Variable que almacenará la dirección MAC resuelta (bytes) recibida en el ARP Reply, o None
resolvedMAC = None

# Variable booleana bandera: True mientras esperamos respuesta ARP; False al recibirla
awaitingResponse = False

# Semáforo para proteger las lecturas y escrituras concurrentes en la caché ARP
cacheLock = Lock()

# Caché de ARP: almacena asociaciones { IP_entero (int) : MAC_bytes (bytes) }.
# ExpiringDict elimina automáticamente las entradas tras 10 segundos de inactividad.
cache = ExpiringDict(max_len=100, max_age_seconds=10)


def getIP(interface:str) -> int:
    '''
        Nombre: getIP
        Descripción: Esta función obtiene la dirección IP asociada a una interfaz. Esta funció NO debe ser modificada
        Argumentos:
            -interface: nombre de la interfaz
        Retorno: Entero de 32 bits con la dirección IP de la interfaz
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   1. initARP(interface) en arp.py: para obtener y guardar myIP.
    #   2. practica2.py en el comando 'g': para enviar un ARP gratuito de nuestra IP.
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - fcntl.ioctl: llamada al sistema de Linux con el código SIOCGIFADDR (0x8915).
    #
    # PARÁMETROS:
    #   - interface (str): Nombre de la interfaz (ej: "eth0", "h1-eth0").
    #
    # RETORNO:
    #   - int: Dirección IPv4 de 32 bits en orden de red big-endian (formato '!I').
    # ==========================================================================
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR: constante de kernel para consultar la IP de una interfaz
        struct.pack('256s', (interface[:15].encode('utf-8')))
    )[20:24]   # La respuesta del kernel contiene 20 bytes de cabecera; los 4 siguientes son la IP
    s.close()
    return struct.unpack('!I',ip)[0]


def printCache()->None:
    '''
        Nombre: printCache
        Descripción: Esta función imprime la caché ARP
        Argumentos: Ninguno
        Retorno: Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py cuando el usuario pulsa la opción 'p'.
    #
    # PARÁMETROS / RETORNO:
    #   - Ninguno. Imprime por pantalla la tabla con formato IP | MAC.
    #
    # DETALLES DE IMPLEMENTACIÓN:
    #   - Se protege la iteración del diccionario con `with cacheLock:`.
    #   - socket.inet_ntoa convierte el entero de 32 bits a cadena "X.X.X.X".
    #   - '{:02X}'.format(b) formatea cada byte de la MAC en hexadecimal de 2 dígitos.
    # ==========================================================================
    print('{:>12}\t\t{:>12}'.format('IP','MAC'))
    with cacheLock:
        for k in cache:
            if k in cache:
                print ('{:>12}\t\t{:>12}'.format(socket.inet_ntoa(struct.pack('!I',k)),':'.join(['{:02X}'.format(b) for b in cache[k]])))



def processARPRequest(data:bytes,MAC:bytes)->None:
    '''
        Nombre: processARPRequest
        Decripción: Esta función procesa una petición ARP. Esta función debe realizar, al menos, las siguientes tareas:
            -Extraer la MAC origen contenida en la petición ARP
            -Si la MAC origen de la trama ARP no es la misma que la recibida del nivel Ethernet retornar
            -Extraer la IP origen contenida en la petición ARP
            -Extraer la IP destino contenida en la petición ARP
            -Comprobar si la IP destino de la petición ARP es la propia IP:
                -Si no es la propia IP retornar
                -Si es la propia IP:
                    -Construir una respuesta ARP llamando a createARPReply (descripción más adelante)
                    -Enviar la respuesta ARP usando el nivel Ethernet (sendEthernetFrame)
        Argumentos:
            -data: bytearray con el contenido de la trama ARP (después de la cabecera común)
            -MAC: dirección MAC origen extraída por el nivel Ethernet
        Retorno: Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - process_arp_frame() cuando el opcode del paquete ARP es 1 (ARP Request).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   1. createARPReply(sender_ip, sender_mac): construye el paquete de respuesta (Opcode 2).
    #   2. sendEthernetFrame(respuesta, len(respuesta), 0x0806, sender_mac): envía la respuesta unicast.
    #
    # PARÁMETROS:
    #   - data (bytes): Paquete ARP completo de 28 bytes.
    #       * data[8:14]  = Sender MAC (quien pregunta)
    #       * data[14:18] = Sender IP (IP de quien pregunta)
    #       * data[18:24] = Target MAC (todo ceros)
    #       * data[24:28] = Target IP (IP por la que están preguntando)
    #   - MAC (bytes): Dirección MAC origen obtenida de la cabecera Ethernet de nivel 2.
    #
    # RETORNO:
    #   - Ninguno.
    #
    # COMPROBACIÓN ANTI-SPOOFING (PREGUNTA CLAVE DE EXAMEN):
    #   "¿Por qué se comprueba sender_mac == MAC?"
    #   Respuesta: Para verificar que la dirección de nivel de enlace (Ethernet) coincide
    #   con la dirección declarada dentro del paquete ARP, evitando ataques de suplantación.
    # ==========================================================================
    global myIP
    
    # 1. Extraemos la IP destino contenida en la petición ARP (bytes 24 a 27)
    target_ip = struct.unpack('!I', data[24:28])[0]
    
    # 2. Si la IP por la que preguntan es la nuestra, debemos contestar
    if target_ip == myIP:
        # Extraemos la MAC del emisor del paquete ARP
        sender_mac = data[8:14] 
        
        # Validación de seguridad Anti-Spoofing: debe coincidir con la MAC de la trama Ethernet
        if sender_mac != MAC:
            return
            
        # Extraemos la IP del emisor (a quien debemos dirigir la respuesta)
        sender_ip = struct.unpack('!I', data[14:18])[0]  
        
        # 3. Construimos el paquete ARP Reply
        respuesta = createARPReply(sender_ip, sender_mac) 
        
        # 4. Enviamos la respuesta por Ethernet directamente (unicast) al equipo que preguntó
        sendEthernetFrame(respuesta, len(respuesta), 0x0806, sender_mac)
   
   
def processARPReply(data:bytes,MAC:bytes)->None:
    '''
        Nombre: processARPReply
        Decripción: Esta función procesa una respuesta ARP. Esta función debe realizar, al menos, las siguientes tareas:
            -Extraer la MAC origen contenida en la petición ARP
            -Si la MAC origen de la trama ARP no es la misma que la recibida del nivel Ethernet retornar
            -Extraer la IP origen contenida en la petición ARP
            -Extraer la MAC destino contenida en la petición ARP
            -Extraer la IP destino contenida en la petición ARP
            -Comprobar si la IP destino de la petición ARP es la propia IP:
                -Si no es la propia IP retornar
                -Si es la propia IP:
                    -Comprobar si la IP origen se corresponde con la solicitada (requestedIP). Si no se corresponde retornar
                    -Copiar la MAC origen a la variable global resolvedMAC
                    -Añadir a la caché ARP la asociación MAC/IP.
                    -Cambiar el valor de la variable awaitingResponse a False
                    -Cambiar el valor de la variable requestedIP a None
        Las variables globales (requestedIP, awaitingResponse y resolvedMAC) son accedidas concurrentemente por la función ARPResolution y deben ser protegidas mediante un Lock.
        Argumentos:
            -data: bytearray con el contenido de la trama ARP (después de la cabecera común)
            -MAC: dirección MAC origen extraída por el nivel Ethernet
        Retorno: Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - process_arp_frame() cuando el opcode del paquete ARP es 2 (ARP Reply).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - Actualiza la caché con `cacheLock` y las variables globales con `globalLock`.
    #
    # PARÁMETROS:
    #   - data (bytes): Paquete ARP completo de 28 bytes:
    #       * data[8:14]  = Sender MAC (la MAC que estábamos buscando y nos responde)
    #       * data[14:18] = Sender IP (la IP de quien nos contesta)
    #       * data[18:24] = Target MAC (nuestra MAC)
    #       * data[24:28] = Target IP (nuestra IP)
    #   - MAC (bytes): MAC origen de nivel 2 extraída de la cabecera Ethernet.
    #
    # RETORNO:
    #   - Ninguno.
    #
    # MECANISMO DE SINCRONIZACIÓN:
    #   Al poner `awaitingResponse = False` dentro de `globalLock`, la función `ARPResolution`
    #   (que está en el hilo principal haciendo sondeo en su bucle while) detecta inmediatamente
    #   que la respuesta ha llegado y devuelve `resolvedMAC`.
    # ==========================================================================
    global requestedIP,resolvedMAC,awaitingResponse,cache
    
    # 1. Extraemos la MAC origen del paquete ARP y verificamos Anti-Spoofing
    sender_mac = data[8:14]
    if sender_mac != MAC:
        return
        
    # 2. Extraemos la IP del emisor
    sender_ip = struct.unpack('!I', data[14:18])[0]
    
    # 3. Extraemos MAC destino e IP destino del paquete
    target_mac = data[18:24]
    target_ip = struct.unpack('!I', data[24:28])[0]
    
    # 4. Solo procesamos si la respuesta va dirigida expresamente a nuestra IP
    if target_ip == myIP:
        # Protegemos el acceso concurrente con el hilo de ARPResolution
        with globalLock:
            # Descartamos respuestas no solicitadas o de IPs distintas a la que estamos resolviendo
            if sender_ip != requestedIP:
                return
                
            # Guardamos la MAC resuelta en la variable global compartida
            resolvedMAC = sender_mac            
            
            # Almacenamos la asociación IP -> MAC en la tabla caché protegida por su propio cerrojo
            with cacheLock:
                cache[sender_ip] = sender_mac                
                
            # Señalizamos a ARPResolution que ya se ha recibido la respuesta
            awaitingResponse = False                
            requestedIP = None



def createARPRequest(ip:int) -> bytes:
    '''
        Nombre: createARPRequest
        Descripción: Esta función construye una petición ARP y devuelve la trama con el contenido.
        Argumentos: 
            -ip: dirección a resolver 
        Retorno: Bytes con el contenido de la trama de petición ARP
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - ARPResolution(ip) para generar los bytes de la petición que se enviará por Ethernet.
    #
    # PARÁMETROS:
    #   - ip (int): Entero de 32 bits con la dirección IP que se quiere resolver.
    #
    # RETORNO:
    #   - bytes: Trama ARP Request de 28 bytes lista para encapsular en Ethernet.
    #
    # CAMPOS DEL PAQUETE CONSTRUIDO:
    #   [ARPHeader (6B)] : HW=Ethernet (0x0001), Proto=IPv4 (0x0800), HWlen=6, Protolength=4
    #   [opcode (2B)]    : 0x0001 (Request)
    #   [sender_mac (6B)]: myMAC (nuestra dirección MAC física)
    #   [sender_ip (4B)] : myIP (nuestra dirección IP)
    #   [target_mac (6B)]: 00:00:00:00:00:00 (se desconoce, se rellena con 6 ceros)
    #   [target_ip (4B)] : ip buscada (empaquetada en 4 bytes con '!I')
    # ==========================================================================
    global myMAC,myIP    
    primeros6 = ARPHeader
    opcode = struct.pack('!H', 1) # Opcode 1 = Request
    
    sender_mac = myMAC
    sender_ip = struct.pack('!I', myIP)
    
    target_mac = bytes([0x00] * 6)  # Destino físico desconocido -> 6 ceros
    target_ip = struct.pack('!I', ip)
    
    frame = primeros6 + opcode + sender_mac + sender_ip + target_mac + target_ip
    return frame


def createARPReply(IP:int ,MAC:bytes) -> bytes:
    '''
        Nombre: createARPReply
        Descripción: Esta función construye una respuesta ARP y devuelve la trama con el contenido.
        Argumentos: 
            -IP: dirección IP a la que contestar
            -MAC: dirección MAC a la que contestar
        Retorno: Bytes con el contenido de la trama de petición ARP
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - processARPRequest(...) cuando alguien en la red pregunta por nuestra IP.
    #
    # PARÁMETROS:
    #   - IP (int): Dirección IP de 32 bits del equipo solicitante (Target IP en la respuesta).
    #   - MAC (bytes): Dirección MAC de 6 bytes del equipo solicitante (Target MAC en la respuesta).
    #
    # RETORNO:
    #   - bytes: Trama ARP Reply de 28 bytes lista para transmitir por Ethernet.
    #
    # CAMPOS DEL PAQUETE CONSTRUIDO:
    #   [ARPHeader (6B)] : Cabecera común fija
    #   [opcode (2B)]    : 0x0002 (Reply / Respuesta)
    #   [sender_mac (6B)]: myMAC (nuestra MAC, la dirección que el solicitante buscaba)
    #   [sender_ip (4B)] : myIP (nuestra IP)
    #   [target_mac (6B)]: MAC recibida por parámetro (la MAC de quien preguntó)
    #   [target_ip (4B)] : IP recibida por parámetro (la IP de quien preguntó)
    # ==========================================================================
    global myMAC, myIP
    primeros6 = ARPHeader
    opcode = struct.pack('!H', 2) # Opcode 2 = Reply
    
    sender_mac = myMAC
    sender_ip = struct.pack('!I', myIP)
    
    target_mac = MAC
    target_ip = struct.pack('!I', IP)
    
    frame = primeros6 + opcode + sender_mac + sender_ip + target_mac + target_ip
    return frame


def process_arp_frame(us:ctypes.c_void_p,header:pcap_pkthdr,data:bytes,srcMac:bytes) -> None:
    '''
        Nombre: process_arp_frame
        Descripción: Esta función procesa las tramas ARP. 
            Se ejecutará por cada trama Ethenet que se reciba con Ethertype 0x0806 (si ha sido registrada en initARP). 
            Esta función debe realizar, al menos, las siguientes tareas:
                -Extraer la cabecera común de ARP (6 primeros bytes) y comprobar que es correcta
                -Extraer el campo opcode
                -Si opcode es 0x0001 (Request) llamar a processARPRequest (ver descripción más adelante)
                -Si opcode es 0x0002 (Reply) llamar a processARPReply (ver descripción más adelante)
                -Si es otro opcode retornar de la función
                -En caso de que no exista retornar
        Argumentos:
            -us: Datos de usuario pasados desde la llamada de pcap_loop. En nuestro caso será None
            -header: cabecera pcap_pktheader
            -data: array de bytes con el contenido de la trama ARP
            -srcMac: MAC origen de la trama Ethernet que se ha recibido
        Retorno: Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - process_Ethernet_frame() en ethernet.py (al llegar una trama con Ethertype 0x0806).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - processARPRequest(data, srcMac): si opcode == 1 (Petición).
    #   - processARPReply(data, srcMac):   si opcode == 2 (Respuesta).
    #
    # PARÁMETROS:
    #   - us: Datos de usuario (None).
    #   - header: Estructura de pcap con metadatos.
    #   - data (bytes): Payload ARP de 28 bytes (sin cabecera Ethernet).
    #   - srcMac (bytes): Dirección MAC origen del nivel de enlace.
    #
    # VALIDACIONES DE SEGURIDAD EXIGIDAS POR EL ENUNCIADO:
    #   1. len(data) >= 28: Asegura que el paquete tenga el tamaño mínimo de un paquete ARP.
    #   2. data[0:6] == ARPHeader: Verifica que corresponda a Ethernet/IPv4.
    # ==========================================================================
    
    # 1. Validación de tamaño mínimo y cabecera fija
    if len(data) < 28 or data[0:ARP_HLEN] != ARPHeader:
        return
        
    # 2. Extraemos el Opcode (bytes 6 y 7 en big-endian)
    opcode = struct.unpack('!H', data[6:8])[0]
    
    # 3. Derivamos según el tipo de operación ARP
    if opcode == 1:
        processARPRequest(data, srcMac)
    elif opcode == 2:
        processARPReply(data, srcMac)
    else:
        pass


def initARP(interface:str) -> int:
    '''
        Nombre: initARP
        Descripción: Esta función construirá inicializará el nivel ARP. Esta función debe realizar, al menos, las siguientes tareas:
            -Registrar la función del callback process_arp_frame con el Ethertype 0x0806
            -Obtener y almacenar la dirección MAC e IP asociadas a la interfaz especificada
            -Realizar una petición ARP gratuita y comprobar si la IP propia ya está asignada. En caso positivo se debe devolver error.
            -Marcar la variable de nivel ARP inicializado a True
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py durante el arranque (PASO 3 del orden de inicialización).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - registerEthCallback(process_arp_frame, 0x0806) en ethernet.py.
    #   - getIP(interface) y getHwAddr(interface).
    #   - ARPResolution(myIP): realiza la comprobación de ARP Gratuito.
    #
    # PARÁMETROS:
    #   - interface (str): Nombre de la tarjeta de red (ej: "eth0").
    #
    # RETORNO:
    #   -  0: Nivel ARP inicializado correctamente e IP libre de conflictos.
    #   - -1: Error (conflicto detectado: otro equipo ya está usando nuestra IP).
    #
    # ¿QUÉ ES EL ARP GRATUITO? (PREGUNTA OBLIGATORIA DE EXAMEN):
    #   - Consiste en emitir una resolución ARP preguntando por NUESTRA PROPIA IP.
    #   - Si nadie responde (ARPResolution devuelve None), significa que la IP está libre.
    #   - Si alguien responde (devuelve una MAC), hay un CONFLICTO DE IP en la red y se aborta.
    # ==========================================================================
    global myIP,myMAC,arpInitialized
    
    # 1. Registramos en el nivel Ethernet el callback para tramas ARP (Ethertype 0x0806)
    registerEthCallback(process_arp_frame, 0x0806)
    
    # 2. Leemos y almacenamos nuestra dirección IP y MAC local
    myIP = getIP(interface)
    myMAC = getHwAddr(interface)
    
    # 3. Verificación de IP duplicada mediante ARP Gratuito
    if ARPResolution(myIP) is not None:
        logging.error("La IP ya está siendo utilizada .")
        return -1        
        
    # 4. Marcamos la variable de nivel ARP como inicializado
    arpInitialized = True  
    return 0


def ARPResolution(ip:int) -> bytes:
    '''
        Nombre: ARPResolution
        Descripción: Esta función intenta realizar una resolución ARP para una IP dada y devuelve la dirección MAC asociada a dicha IP 
            o None en caso de que no haya recibido respuesta. Esta función debe realizar, al menos, las siguientes tareas:
                -Comprobar si la IP solicitada existe en la caché:
                -Si está en caché devolver la información de la caché
                -Si no está en la caché:
                    -Construir una petición ARP llamando a la función createARPRequest (descripción más adelante)
                    -Enviar dicha petición
                    -Comprobar si se ha recibido respuesta o no:
                        -Si no se ha recibido respuesta reenviar la petición hasta un máximo de 3 veces. Si no se recibe respuesta devolver None
                        -Si se ha recibido respuesta devolver la dirección MAC
            Esta función necesitará comunicarse con el la función de recepción (para comprobar si hay respuesta y la respuesta en sí) mediante 3 variables globales:
                -awaitingResponse: indica si está True que se espera respuesta. Si está a False quiere decir que se ha recibido respuesta
                -requestedIP: contiene la IP por la que se está preguntando
                -resolvedMAC: contiene la dirección MAC resuelta (en caso de que awaitingResponse) sea False.
            Como estas variables globales se leen y escriben concurrentemente deben ser protegidas con un Lock
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   1. practica2.py en el comando 'a <IP>': resuelve una IP para mostrar su MAC.
    #   2. initARP(interface) en el arranque: resuelve myIP para el ARP Gratuito.
    #   3. practica2.py en el comando 'g': envía ARP Gratuito bajo demanda.
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - createARPRequest(ip): ensambla el paquete de petición.
    #   - sendEthernetFrame(... broadcastAddr): emite la petición en difusión.
    #
    # PARÁMETROS:
    #   - ip (int): Dirección IPv4 de 32 bits a resolver.
    #
    # RETORNO:
    #   - bytes (6B): Dirección MAC resuelta si hubo respuesta.
    #   - None: Si tras 3 intentos no hubo ninguna respuesta (host inaccesible o apagado).
    #
    # ESTRATEGIA DE ESPERA ACTIVA SIN DESPERDICIO DE TIEMPO:
    #   En cada uno de los 3 intentos espera como máximo 1.0 segundo. Realiza comprobaciones
    #   cada 100 ms (time.sleep(0.1)). Si el hilo receptor recibe el ARP Reply a los 5 ms,
    #   awaitingResponse pasa a False y la función retorna inmediatamente sin agotar el segundo.
    # ==========================================================================
    global requestedIP,awaitingResponse,resolvedMAC
    
    # 1. Consulta previa en la caché: si ya la conocemos, no emitimos tráfico a la red
    with cacheLock:
        if ip in cache:
            return cache[ip]
            
    # 2. Inicializamos las variables de sincronización compartidas bajo el cerrojo global
    with globalLock:
        requestedIP = ip
        awaitingResponse = True
        resolvedMAC = None        
        
    # 3. Construimos el paquete ARP Request (se reutiliza en los reintentos)
    peticion = createARPRequest(ip)
    
    # 4. Bucle de hasta 3 intentos de transmisión
    for intento in range(3):       
        # Enviamos la petición en difusión (broadcast = FF:FF:FF:FF:FF:FF) con Ethertype 0x0806
        sendEthernetFrame(peticion, len(peticion), 0x0806, broadcastAddr)       
        
        # Esperamos hasta 1.0 segundo comprobando cada 0.1s si llegó la respuesta
        espera = 0.0
        while espera < 1.0:
            with globalLock:
                # Si el hilo receptor puso awaitingResponse a False, la MAC ya está disponible
                if not awaitingResponse:
                    return resolvedMAC
                    
            time.sleep(0.1)
            espera += 0.1           
            
    # 5. Si se agotaron los 3 intentos sin respuesta, limpiamos el estado y devolvemos None
    with globalLock:
        requestedIP = None
        awaitingResponse = False
        
    return None