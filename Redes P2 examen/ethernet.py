'''
    ethernet.py
    Implementación del nivel Ethernet y funciones auxiliares para el envío y recepción de tramas Ethernet.
    Autor: Jorge Palomino y Raul Matellano
    2019 EPS-UAM
'''

# ==============================================================================
# RESUMEN GENERAL Y GUÍA DE ESTUDIO: ethernet.py (NIVEL 2 - ENLACE DE DATOS)
# ==============================================================================
# Este módulo implementa la capa de enlace (Nivel 2 de la pila OSI/TCP-IP).
# Su cometido fundamental es:
#   1. Interactuar con la tarjeta de red física o virtual a través de libpcap (rc1_pcap.py).
#   2. En recepción: capturar tramas crudas, filtrar las que no sean para nosotros,
#      desencapsular la cabecera Ethernet y despachar los datos al protocolo superior
#      adecuado (ARP o EthMsg) según el campo Ethertype.
#   3. En transmisión: recibir datos del nivel superior, añadir la cabecera Ethernet
#      [MAC destino (6B) + MAC origen (6B) + Ethertype (2B)], aplicar relleno de ceros
#      si no alcanza los 60 bytes mínimos e inyectar la trama en el medio físico.
#
# ------------------------------------------------------------------------------
# FLUJO DE LLAMADAS Y RELACIÓN ENTRE FUNCIONES (QUIÉN LLAMA A QUIÉN):
# ------------------------------------------------------------------------------
# [ARRANQUE]:
#   practica2.py 
#       └──> startEthernetLevel(interface)
#               ├──> getHwAddr(interface) [obtiene MAC local]
#               ├──> pcap_open_live(...) [abre captura en modo promiscuo]
#               └──> rxThread.start() [lanza hilo receptor en segundo plano]
#
# [RECEPCIÓN CONTINUA]:
#   rxThread (en segundo plano)
#       └──> pcap_loop(handle, -1, process_frame, None)
#               └──> (por cada trama que llega) ──> process_frame(...)
#                       └──> threading.Thread(target=process_Ethernet_frame).start()
#                               └──> process_Ethernet_frame(...)
#                                       ├──> Filtra: ¿destino == mi_MAC o Broadcast?
#                                       ├──> Extrae Ethertype [12:14]
#                                       └──> EthernetProtocols[tipo](us, header, payload, srcMac)
#                                               ├── si 0x0806 ──> process_arp_frame(...) en arp.py
#                                               └── si 0x0AA0 ──> process_ethMsg_frame(...) en ethmsg.py
#
# [TRANSMISIÓN]:
#   arp.py / ethmsg.py
#       └──> sendEthernetFrame(data, length, etherType, dstMac)
#               ├──> Ensambla trama [dstMac(6B) + srcMac(6B) + etherType(2B) + payload]
#               ├──> Padding si longitud < 60B (añade ceros)
#               ├──> Error si longitud > 1514B
#               └──> pcap_inject(handle, frame, len(frame)) [envío físico]
#
# [CIERRE]:
#   practica2.py
#       └──> stopEthernetLevel()
#               ├──> rxThread.stop() [llama a pcap_breakloop]
#               └──> pcap_close(handle) [libera descriptor pcap]
# ==============================================================================

from rc1_pcap import *   # Importa el wrapper Python de la librería C libpcap (pcap_open_live, pcap_inject, etc.)
import logging
import socket
import struct
from binascii import hexlify
import threading 

# ------------------------------------------------------------------------------
# CONSTANTES Y PARÁMETROS DEL PROTOCOLO ETHERNET (IEEE 802.3 / DIX Ethernet II)
# ------------------------------------------------------------------------------

# Tamaño máximo de una trama Ethernet (MTU 1500 bytes de datos + 14 bytes cabecera = 1514 bytes)
ETH_FRAME_MAX = 1514

# Tamaño mínimo de una trama Ethernet según estándar IEEE 802.3 (64 bytes con CRC de 4 bytes;
# al excluir el CRC generado por hardware, la trama mínima transmitida por software es de 60 bytes).
ETH_FRAME_MIN = 60

# Modos de captura de libpcap:
PROMISC = 1       # Modo promiscuo: captura TODO el tráfico que circula por la LAN, no solo el dirigido a nuestra MAC
NO_PROMISC = 0    # Modo no promiscuo: solo captura tráfico propio o broadcast
TO_MS = 10        # Timeout de lectura en milisegundos para pcap_open_live

# Dirección MAC de difusión (Broadcast): FF:FF:FF:FF:FF:FF (6 bytes a 0xFF).
# Cualquier trama con esta MAC de destino es procesada por todas las tarjetas de red de la LAN.
broadcastAddr = bytes([0xFF]*6)

# Diccionario que almacena la tabla de protocolos registrados en Nivel 2:
#   Clave:   Ethertype (entero de 16 bits, ej: 0x0806 para ARP, 0x0AA0 para EthMsg)
#   Valor:   Función de callback a invocar cuando llegue una trama con dicho Ethertype
EthernetProtocols = {}


def getHwAddr(interface:str):
    '''
        Nombre: getHwAddr
        Descripción: Esta función obtiene la dirección MAC asociada a una interfaz
        Argumentos:
            -interface: Cadena con el nombre de la interfaz
        Retorno:
            -Dirección MAC de la interfaz
        NO MODIFICAR
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   1. startEthernetLevel(interface) en ethernet.py (guarda macAddress global).
    #   2. initARP(interface) en arp.py (guarda myMAC global).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - socket.socket(socket.AF_PACKET, socket.SOCK_RAW): llamada al kernel Linux.
    #   - s.getsockname(): devuelve (interfaz, proto, tipo, hatype, MAC_en_bytes).
    #
    # PARÁMETROS:
    #   - interface (str): Nombre del dispositivo de red (ej: "eth0", "h1-eth0").
    #
    # RETORNO:
    #   - bytes (6 bytes): Dirección física MAC de la interfaz (ej: b'\x00\x00\x00\x00\x00\x01').
    # ==========================================================================
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((interface,0))
    mac =  (s.getsockname()[4])
    s.close()
    return mac


def process_Ethernet_frame(us:ctypes.c_void_p,header:pcap_pkthdr,data:bytes) -> None:
    '''
        Nombre: process_Ethernet_frame
        Descripción: Esta función se ejecutará cada vez que llegue una trama Ethernet. 
            Esta función debe realizar, al menos, las siguientes tareas:
                -Extraer los campos de dirección Ethernet destino, origen y ethertype
                -Comprobar si la dirección destino es la propia o la de broadcast. En caso de que la trama no vaya en difusión o no sea para nuestra interfaz la descartaremos (haciendo un return).
                -Comprobar si existe una función de callback de nivel superior asociada al Ethertype de la trama:
                    -En caso de que exista, llamar a la función de nivel superior con los parámetros que corresponde:
                        -us (datos de usuario)
                        -header (cabecera pcap_pktheader)
                        -payload (datos de la trama excluyendo la cabecera Ethernet)
                        -dirección Ethernet origen
                    -En caso de que no exista retornar
        Argumentos:
            -us: datos de usuarios pasados desde pcap_loop (en nuestro caso será None)
            -header: estructura pcap_pkthdr que contiene los campos len, caplen y ts.
            -data: bytearray con el contenido de la trama Ethernet
        Retorno:
            -Ninguno
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - process_frame() mediante un hilo nuevo independiente (threading.Thread).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - Al callback del nivel superior registrado en EthernetProtocols[tipo]:
    #       * Si tipo == 0x0806 ──> process_arp_frame(us, header, payload, origen) en arp.py
    #       * Si tipo == 0x0AA0 ──> process_ethMsg_frame(us, header, payload, origen) en ethmsg.py
    #
    # PARÁMETROS:
    #   - us (ctypes.c_void_p): Puntero opcional a datos de usuario de libpcap (en nuestro caso None).
    #   - header (pcap_pkthdr): Metadatos de captura de libpcap:
    #       * header.len: Longitud original del paquete en el cable.
    #       * header.caplen: Bytes efectivamente capturados.
    #       * header.ts.tv_sec: Timestamp segundos (Unix epoch).
    #       * header.ts.tv_usec: Timestamp microsegundos.
    #   - data (bytes): Trama Ethernet completa en crudo recibida del cable:
    #       * data[0:6]   = MAC Destino (6 bytes)
    #       * data[6:12]  = MAC Origen (6 bytes)
    #       * data[12:14] = Ethertype (2 bytes, big-endian)
    #       * data[14:]   = Payload de nivel superior (datos sin la cabecera Ethernet)
    #
    # RETORNO:
    #   - None (los datos se propagan hacia arriba mediante llamada a callback).
    #
    # PREGUNTA CLAVE DE EXAMEN:
    #   "¿Por qué se pasa data[14:] y no data entero al callback superior?"
    #   Respuesta: Por el principio de abstracción por capas: el nivel superior (ARP, EthMsg)
    #   no debe lidiar con la cabecera de nivel 2 Ethernet, solo con sus propios datos.
    # ==========================================================================
    global macAddress, broadcastAddr, EthernetProtocols
    
    # 1. Extraemos direcciones MAC destino y origen de la cabecera Ethernet
    destino = data[0:6]  
    origen = data[6:12] 
    
    # 2. FILTRADO: Si la trama no va dirigida a nuestra MAC ni es una difusión (Broadcast),
    # la descartamos inmediatamente (return) para no sobrecargar el sistema.
    if destino != macAddress and destino != broadcastAddr:
        return
        
    # 3. Leemos el campo Ethertype (bytes 12 y 13) en orden de red big-endian ('!H' = unsigned short 16 bits)
    tipo = struct.unpack('!H', data[12:14])[0]
    
    # 4. Comprobamos si hay un protocolo registrado para este Ethertype
    if tipo in EthernetProtocols:
        # Desencapsulamos: quitamos los 14 bytes de la cabecera Ethernet
        payload = data[14:] 
        
        # Recuperamos la función de callback asociada y la invocamos
        protocolo = EthernetProtocols[tipo]
        protocolo(us, header, payload, origen)
    

def process_frame(us:ctypes.c_void_p,header:pcap_pkthdr,data:bytes) -> None:
    '''
        Nombre: process_frame
        Descripción: Esta función se pasa a pcap_loop y se ejecutará cada vez que llegue una trama. La función
        ejecutará la función process_Ethernet_frame en un hilo nuevo para evitar interbloqueos entre 2 recepciones
        consecutivas de tramas dependientes. Esta función NO debe modifciarse
        Argumentos:
            -us: datos de usuarios pasados desde pcap_loop (en nuestro caso será None)
            -header: estructura pcap_pkthdr que contiene los campos len, caplen y ts.
            -data: bytearray con el contenido de la trama Ethernet
        Retorno:
            -Ninguno
        NO MODIFICAR
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - La librería libpcap desde C a través del bucle pcap_loop() en rxThread.
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - Lanza un nuevo hilo con threading.Thread que ejecuta process_Ethernet_frame.
    #
    # ¿POR QUÉ SE USA UN HILO NUEVO? (PREGUNTA TÍPICA DE EXAMEN ORAL):
    #   - pcap_loop se ejecuta en un único hilo de captura. Si process_Ethernet_frame
    #     tardara en responder o necesitara esperar una respuesta de red (como en una
    #     resolución ARP donde se envía un Request y se espera un Reply), pcap_loop
    #     quedaría completamente BLOQUEADO y sería INCAPAZ de capturar la respuesta
    #     entrante, causando un INTERBLOQUEO (deadlock).
    #   - Al crear un hilo nuevo, process_frame retorna al instante a libpcap para que
    #     siga escuchando el siguiente paquete sin perder tráfico.
    # ==========================================================================
    threading.Thread(target=process_Ethernet_frame,args=(us,header,data)).start()


class rxThread(threading.Thread): 
    ''' Clase que implementa un hilo de recepción. De esta manera al iniciar el nivel Ethernet
        podemos dejar un hilo con pcap_loop que reciba los paquetes sin bloquear el envío.
        En esta clase NO se debe modificar código
    '''
    # ==========================================================================
    # ¿QUIÉN INSTANCIA Y UTILIZA ESTA CLASE?:
    #   - startEthernetLevel(): crea la instancia `recvThread = rxThread()`,
    #     marca `daemon = True` y la arranca con `recvThread.start()`.
    #   - stopEthernetLevel(): llama a `recvThread.stop()`.
    # ==========================================================================
    def __init__(self): 
        threading.Thread.__init__(self) 
              
    def run(self): 
        global handle
        # pcap_loop recibe handle de captura, cnt=-1 (bucle infinito hasta breakloop),
        # función de callback (process_frame) y argumentos de usuario (None).
        if handle is not None:
            pcap_loop(handle,-1,process_frame,None)

    def stop(self):
        global handle
        # pcap_breakloop manda una señal interna a libpcap para que pcap_loop salga de su bucle.
        if handle is not None:
            pcap_breakloop(handle)


def registerEthCallback(callback_func: Callable[[ctypes.c_void_p,pcap_pkthdr,bytes],None], ethertype:int) -> None:
    '''
        Nombre: registerCallback
        Descripción: Esta función recibirá el nombre de una función y su valor de ethertype asociado y añadirá en la tabla 
            (diccionario) de protocolos de nivel superior el dicha asociación. 
            Este mecanismo nos permite saber a qué función de nivel superior debemos llamar al recibir una trama de determinado tipo. 
            Por ejemplo, podemos registrar una función llamada process_IP_datagram asociada al Ethertype 0x0800 y otra llamada process_arp_packet 
            asocaida al Ethertype 0x0806. 
        Argumentos:
            -callback_fun: función de callback a ejecutar cuando se reciba el Ethertype especificado. 
                La función que se pase como argumento debe tener el siguiente prototipo: funcion(us,header,data,srcMac)
                Dónde:
                    -us: son los datos de usuarios pasados por pcap_loop (en nuestro caso este valor será siempre None)
                    -header: estructura pcap_pkthdr que contiene los campos len, caplen y ts.
                    -data: payload de la trama Ethernet. Es decir, la cabecera Ethernet NUNCA se pasa hacia arriba.
                    -srcMac: dirección MAC que ha enviado la trama actual.
                La función no retornará nada. Si una trama se quiere descartar basta con hacer un return sin valor y dejará de procesarse.
            -ethertype: valor de Ethernetype para el cuál se quiere registrar una función de callback.
        Retorno: Ninguno 
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   1. initARP(interface) en arp.py: registerEthCallback(process_arp_frame, 0x0806)
    #   2. initEthMsg(interface) en ethmsg.py: registerEthCallback(process_ethMsg_frame, 0x0AA0)
    #
    # PARÁMETROS:
    #   - callback_func (función): Puntero a función con prototipo f(us, header, data, srcMac).
    #   - ethertype (int): Número de protocolo de 16 bits (ej: 0x0806 = ARP, 0x0AA0 = EthMsg).
    #
    # RETORNO:
    #   - Ninguno. Guarda la asociación en el diccionario global EthernetProtocols.
    # ==========================================================================
    global EthernetProtocols
    EthernetProtocols[ethertype] = callback_func    


def startEthernetLevel(interface:str) -> int:
    '''
        Nombre: startEthernetLevel
        Descripción: Esta función recibe el nombre de una interfaz de red e inicializa el nivel Ethernet. 
            Esta función debe realizar , al menos, las siguientes tareas:
                -Comprobar si el nivel Ethernet ya estaba inicializado (mediante una variable global). Si ya estaba inicializado devolver -1.
                -Obtener y almacenar en una variable global la dirección MAC asociada a la interfaz que se especifica
                -Abrir la interfaz especificada en modo promiscuo usando la librería rc1-pcap
                -Arrancar un hilo de recepción (rxThread) que llame a la función pcap_loop. 
                -Si todo es correcto marcar la variable global de nivel incializado a True
        Argumentos:
            -Interface: nombre de la interfaz sobre la que inicializar el nivel Ethernet
        Retorno: 0 si todo es correcto, -1 en otro caso
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py al arrancar el programa (PASO 1 del orden de inicialización).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - getHwAddr(interface): para leer la MAC física y almacenarla en `macAddress`.
    #   - pcap_open_live(...): función C de libpcap para abrir el descriptor de red.
    #   - rxThread(): crea y arranca el hilo receptor de paquetes en segundo plano.
    #
    # PARÁMETROS:
    #   - interface (str): Nombre de la tarjeta de red (ej: "eth0", "h1-eth0").
    #
    # RETORNO:
    #   -  0: Nivel Ethernet inicializado correctamente.
    #   - -1: Error (ya estaba inicializado o falló pcap_open_live).
    # ==========================================================================
    global macAddress,handle,levelInitialized,recvThread
    handle = None
    logging.debug('Función no implementada')
    
    # 1. Protección contra reinicialización: si ya estaba inicializado devolvemos error
    if 'levelInitialized' in globals() and levelInitialized:     
        return -1
        
    # 2. Obtenemos y guardamos la MAC de nuestra interfaz de red en la variable global
    macAddress = getHwAddr(interface)
    
    # 3. Abrimos la interfaz para captura en modo promiscuo con pcap_open_live
    errbuf = bytearray(256) 
    handle = pcap_open_live(interface, ETH_FRAME_MAX, PROMISC, TO_MS, errbuf)
    if handle is None:
        logging.error("No se pudo abrir pcap")
        return -1
        
    # 4. Marcamos la bandera de nivel inicializado a True
    levelInitialized = True
    
    # 5. Arrancamos el hilo de recepción continua (rxThread) en modo demonio
    # (daemon=True garantiza que si el programa principal termina, el hilo muere solo)
    recvThread = rxThread()
    recvThread.daemon = True
    recvThread.start()
    return 0


def stopEthernetLevel()->int:
    global macAddress,handle,levelInitialized,recvThread
    '''
        Nombre: stopEthernetLevel
        Descripción_ Esta función parará y liberará todos los recursos necesarios asociados al nivel Ethernet. 
            Esta función debe realizar, al menos, las siguientes tareas:
                -Parar el hilo de recepción de paquetes 
                -Cerrar la interfaz (handle de pcap)
                -Marcar la variable global de nivel incializado a False
        Argumentos: Ninguno
        Retorno: 0 si todo es correcto y -1 en otro caso
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   - practica2.py al salir del programa (comando 'q', Ctrl+C o error en initARP).
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - recvThread.stop(): para romper el bucle pcap_loop.
    #   - pcap_close(handle): para cerrar el descriptor de socket y liberar recursos C.
    #
    # RETORNO:
    #   -  0: Nivel Ethernet parado correctamente.
    #   - -1: Error (el nivel no estaba inicializado).
    # ==========================================================================
    # Si el nivel no estaba inicializado, no hay nada que liberar
    if 'levelInitialized' not in globals() or not levelInitialized:
        return -1
        
    # 1. Paramos el hilo receptor enviando breakloop
    if 'recvThread' in globals() and recvThread is not None:
        recvThread.stop()
        
    # 2. Cerramos el handle de captura pcap
    if 'handle' in globals() and handle is not None:
        pcap_close(handle)
        
    # 3. Marcamos la variable de nivel inicializado a False
    levelInitialized = False
    return 0
    

def sendEthernetFrame(data:bytes,length:int,etherType:int,dstMac:bytes) -> int:
    '''
        Nombre: sendEthernetFrame
        Descripción: Esta función construirá una trama Ethernet con lo datos recibidos y la enviará por la interfaz de red. 
            Esta función debe realizar, al menos, las siguientes tareas:
                -Construir la trama Ethernet a enviar (incluyendo cabecera + payload). Los campos propios (por ejemplo la dirección Ethernet origen) 
                    deben obtenerse de las variables que han sido inicializadas en startEthernetLevel
                -Comprobar los límites de Ethernet. Si la trama es muy pequeña se debe rellenar con 0s mientras que 
                    si es muy grande se debe devolver error.
                -Llamar a pcap_inject para enviar la trama y comprobar el retorno de dicha llamada. En caso de que haya error notificarlo
        Argumentos:
            -data: datos útiles o payload a encapsular dentro de la trama Ethernet
            -length: longitud de los datos útiles expresada en bytes
            -etherType: valor de tipo Ethernet a incluir en la trama
            -dstMac: Dirección MAC destino a incluir en la trama que se enviará
        Retorno: 0 si todo es correcto, -1 en otro caso
    '''
    # ==========================================================================
    # ¿QUIÉN LLAMA A ESTA FUNCIÓN?:
    #   1. ethmsg.py ──> sendEthMsg(message): envía tramas broadcast con Ethertype 0x0AA0.
    #   2. arp.py ──> ARPResolution(ip): envía ARP Request en broadcast con Ethertype 0x0806.
    #   3. arp.py ──> processARPRequest(...): envía ARP Reply unicast con Ethertype 0x0806.
    #
    # ¿A QUIÉN LLAMA ESTA FUNCIÓN?:
    #   - pcap_inject(handle, frame, len(frame)): inyecta los bytes directamente en la NIC.
    #
    # PARÁMETROS:
    #   - data (bytes): Payload o datos útiles a encapsular (sin cabecera Ethernet).
    #   - length (int): Longitud en bytes de los datos útiles (el enunciado permite len(data)).
    #   - etherType (int): Código Ethertype de 16 bits (ej: 0x0806 para ARP, 0x0AA0 para EthMsg).
    #   - dstMac (bytes): MAC destino de 6 bytes (FF:FF:FF:FF:FF:FF para difusión o unicast).
    #
    # RETORNO:
    #   -  0: Trama transmitida con éxito.
    #   - -1: Error (supera 1514 bytes o falló pcap_inject).
    #
    # ESTRUCTURA DE LA TRAMA CONSTRUIDA:
    #   [dstMac (6B)] + [macAddress origen (6B)] + [etherType (2B big-endian)] + [data (NB)]
    # ==========================================================================
    global macAddress,handle
    
    # 1. Empaquetamos el Ethertype en 2 bytes en orden de red ('!H' = unsigned short big-endian)
    tipo = struct.pack('!H', etherType)
    
    # 2. Ensamblamos la cabecera Ethernet (14 bytes) junto con el payload de datos
    frame = dstMac + macAddress + tipo + data    
    
    # 3. Comprobación de límite máximo (MTU de 1500 bytes + 14B cabecera = 1514 bytes)
    if len(frame) > ETH_FRAME_MAX:  
        logging.error("Demasiado grande")
        return -1
        
    # 4. Comprobación de límite mínimo: el estándar IEEE 802.3 exige que toda trama en el cable
    # mida al menos 64 bytes (60 bytes sin contar el CRC hardware de 4 bytes).
    # Si mide menos de 60 bytes, rellenamos con bytes a 0x00 (padding).
    if len(frame) < ETH_FRAME_MIN:
        relleno = ETH_FRAME_MIN - len(frame)
        frame += bytes([0x00] * relleno)
        
    # 5. Inyectamos la trama por la interfaz de red usando pcap_inject
    try:
        pcap_inject(handle, frame, len(frame))
    except Exception as e:
        logging.error(f"Error: {e}")
        return -1
        
    return 0
