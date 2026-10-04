'''
    practica1.py
    Muestra el tiempo de llegada de los primeros P paquetes a la interfaz especificada
    como argumento y los vuelca a traza nueva con tiempo actual

    Autor: Jorge Palomino y Raul Matellano
    2026 EPS-UAM
'''

from rc1_pcap import *
import sys
import binascii
import signal
import argparse
from argparse import RawTextHelpFormatter
import time
import logging

ETH_FRAME_MAX = 1514
PROMISC = 1
NO_PROMISC = 0
TO_MS = 10
num_paquete = 0
TIME_OFFSET = 30*60

def signal_handler(nsignal,frame):
    logging.info('Control C pulsado')
    if handle:
        pcap_breakloop(handle)
        

def procesa_paquete(us, header, data):
    global num_paquete, dumper_filtrado, dumper_general, ts_inicio, ts_fin, args
    
    logging.info('Nuevo paquete de {} bytes capturado en el timestamp UNIX {}.{}'.format(header.len, header.ts.tv_sec, header.ts.tv_usec))
    num_paquete += 1
    
    ts_actual = header.ts.tv_sec + (header.ts.tv_usec / 1000000.0)
    if ts_inicio is None:
        ts_inicio = ts_actual
    ts_fin = ts_actual

    if dumper_filtrado is not None and dumper_general is not None:
        if header.caplen >= 14 and data[12] == 0x08 and data[13] == 0x06:
            pcap_dump(dumper_filtrado, header, data)
        else:
            pcap_dump(dumper_general, header, data)
            
    if args.nbytes is not None:
        n_imprimir = min(args.nbytes, header.caplen)
    else:
        n_imprimir = header.caplen

    if n_imprimir > 0:
        cadena_hex = ""
        for i in range(n_imprimir):
            cadena_hex += f"{data[i]:02X} "
            if (i + 1) % 16 == 0:
                logging.info(f"Datos: {cadena_hex.strip()}")
                cadena_hex = ""
        if cadena_hex != "":
            logging.info(f"Datos: {cadena_hex.strip()}")
    
if __name__ == "__main__":
    global dumper_filtrado, dumper_general, args, handle, desc_dead, ts_inicio, ts_fin
    
    parser = argparse.ArgumentParser(description='Captura tráfico de una interfaz ( o lee de fichero) y muestra la longitud y timestamp de los paquetes',
    formatter_class=RawTextHelpFormatter)
    parser.add_argument('--file', dest='tracefile', default=False, help='Fichero pcap a abrir')
    parser.add_argument('--itf', dest='interface', default=False, help='Interfaz a abrir')
    parser.add_argument('--nbytes', dest='nbytes', type=int, default=None, help='Número de bytes a mostrar por paquete')
    parser.add_argument('--debug', dest='debug', default=False, action='store_true', help='Activar Debug messages')
    parser.add_argument('--npkts', dest='npkts', type=int, default=-1, help='Número de paquetes a procesar')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s %(levelname)s]\t%(message)s')
    else:
        logging.basicConfig(level = logging.INFO, format = '[%(asctime)s %(levelname)s]\t%(message)s')
  
    if args.tracefile is False and args.interface is False:
        logging.error('No se ha especificado interfaz ni fichero')
        parser.print_help()
        sys.exit(-1)
        
    if args.tracefile and args.interface:
        logging.error('No se puede especificar una interfaz y un fichero a la vez.')
        sys.exit(-1)

    signal.signal(signal.SIGINT, signal_handler)

    errbuf = bytearray()
    handle = None
    desc_dead = None
    dumper_filtrado = None
    dumper_general = None
    ts_inicio = None
    ts_fin = None
    
    if args.interface:
        handle = pcap_open_live(args.interface, ETH_FRAME_MAX, PROMISC, TO_MS, errbuf)
        if handle is None:
            logging.error(f"Error abriendo la interfaz: {errbuf.decode('utf-8', 'ignore')}")
            sys.exit(-1)     
            
        tiempo_unix_actual = int(time.time())
        desc_dead = pcap_open_dead(DLT_EN10MB, ETH_FRAME_MAX)
        
        nombre_noip = f"capturaNOIP.{args.interface}.{tiempo_unix_actual}.pcap"
        nombre_resto = f"captura.{args.interface}.{tiempo_unix_actual}.pcap"
        
        dumper_filtrado = pcap_dump_open(desc_dead, nombre_noip)
        dumper_general = pcap_dump_open(desc_dead, nombre_resto)
        
    if args.tracefile:
        handle = pcap_open_offline(args.tracefile, errbuf)
        if handle is None:
            logging.error(f"Error abriendo el archivo: {errbuf.decode('utf-8', 'ignore')}")
            sys.exit(-1)
    
    ret = pcap_loop(handle, args.npkts, procesa_paquete, None)
    
    if ret == -1:
        logging.error('Error al capturar un paquete')
    elif ret == -2:
        logging.debug('pcap_breakloop() llamado')
    elif ret == 0:
        logging.debug('No mas paquetes o limite superado')
        
    logging.info('{} paquetes procesados'.format(num_paquete))
    
    if ts_inicio is not None and ts_fin is not None and num_paquete >= 2:
        diferencia = ts_fin - ts_inicio
        logging.info(f"Diferencia de tiempo entre el primer y ultimo paquete: {diferencia:.6f} segundos")

    if dumper_filtrado:
        pcap_dump_close(dumper_filtrado)
    if dumper_general:
        pcap_dump_close(dumper_general)
    if desc_dead:
        pcap_close(desc_dead)
    if handle:
        pcap_close(handle)
