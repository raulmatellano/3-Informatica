'''
    ethmsg.py
    Implementación del protocolo de mensajeria basica para emision de mensajes en tiempo real sobre ethernet.
    Autor: Jorge Palomino y Raul Matellano
    2024 EPS-UAM
'''

from ethernet import *
import logging
import socket
import struct
import fcntl
import time
from threading import Lock
from expiringdict import ExpiringDict   
import datetime


ETHTYPE = 0x0AA0
#Dirección de difusión (Broadcast)
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
    longitud = struct.unpack('!H', data[0:2])[0]
    mensaje = data[2:2+longitud].decode('utf-8')    
    partes_mac = []
    
    for b in srcMac:
        byte_hexadecimal = '{:02X}'.format(b)        
        partes_mac.append(byte_hexadecimal)
        
    mac = ':'.join(partes_mac)    
    segundos = header.ts.tv_sec
    microsegundos = header.ts.tv_usec
    fecha_hora = datetime.datetime.fromtimestamp(segundos).strftime('%Y/%m/%d %H:%M:%S')
    
    print(f"[{fecha_hora}.{microsegundos:06d}] {mac} ({longitud} bytes) : {mensaje}")



def initEthMsg(interface:str) -> int:
    '''
        Nombre: initEthMsg
        Descripción: Esta función construirá inicializará el nivel ethMsg. Esta función debe realizar, al menos, las siguientes tareas:
            -Registrar la función del callback process_ethMsg_frame con el Ethertype ETHTYPE
        Argumentos:   
			interfaz
    '''
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
    global broadcast            
    mensaje = message.encode('utf-8')
    longitud = len(mensaje)
    longitud_bytes = struct.pack('!H', longitud) 
    trama = longitud_bytes + mensaje
    sendEthernetFrame(trama, len(trama), ETHTYPE, broadcast)
    return len(trama)
