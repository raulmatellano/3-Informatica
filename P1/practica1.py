'''
    practica1.py
    Muestra el tiempo de llegada de los primeros P paquetes a la interfaz especificada
    como argumento y los vuelca a traza nueva con tiempo actual

    Autor: Javier Ramos <javier.ramos@uam.es>
    2020 EPS-UAM
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

# Variables globales para controlar los tiempos
primer_ts = None
ultimo_ts = None

def signal_handler(nsignal,frame):
	logging.info('Control C pulsado')
	if handle:
		pcap_breakloop(handle)
		

def procesa_paquete(us,header,data):
	global num_paquete, pdumper_noip, pdumper_rest, primer_ts, ultimo_ts, args
	
	# Corrección del log original para mostrar tv_usec en lugar de repetir tv_sec
	logging.info('Nuevo paquete de {} bytes capturado en el timestamp UNIX {}.{}'.format(header.len, header.ts.tv_sec, header.ts.tv_usec))
	num_paquete += 1
	
	# Registrar timestamps en formato de segundos flotantes
	ts_actual = header.ts.tv_sec + (header.ts.tv_usec / 1000000.0)
	if primer_ts is None:
		primer_ts = ts_actual
	ultimo_ts = ts_actual

	# Escribir el tráfico a los ficheros de captura correspondientes si se está en vivo
	if pdumper_noip is not None and pdumper_rest is not None:
		# Comprobar que el paquete es suficientemente largo y verificar bytes 12 y 13
		if header.caplen >= 14 and data[12] == 0x08 and data[13] == 0x06:
			pcap_dump(pdumper_noip, header, data)
		else:
			pcap_dump(pdumper_rest, header, data)
			
	# Imprimir los N primeros bytes en hexadecimal, mayúsculas y separados
	n_imprimir = min(args.nbytes, header.caplen)
	if n_imprimir > 0:
		cadena_hex = ""
		for i in range(n_imprimir):
			cadena_hex += f"{data[i]:02X} "
			# Limitar a 16 bytes por línea
			if (i + 1) % 16 == 0:
				print(cadena_hex.strip())
				cadena_hex = ""
		# Imprimir los bytes restantes si la línea no llegó a 16
		if cadena_hex != "":
			print(cadena_hex.strip())
		print("") 
	
if __name__ == "__main__":
	global pdumper_noip, pdumper_rest, args, handle, dumper_desc
	parser = argparse.ArgumentParser(description='Captura tráfico de una interfaz ( o lee de fichero) y muestra la longitud y timestamp de los paquetes',
	formatter_class=RawTextHelpFormatter)
	parser.add_argument('--file', dest='tracefile', default=False,help='Fichero pcap a abrir')
	parser.add_argument('--itf', dest='interface', default=False,help='Interfaz a abrir')
	parser.add_argument('--nbytes', dest='nbytes', type=int, default=14,help='Número de bytes a mostrar por paquete')
	parser.add_argument('--npkts', dest='npkts', type=int, default=None,help='Número de paquetes a procesar')
	parser.add_argument('--debug', dest='debug', default=False, action='store_true',help='Activar Debug messages')
	args = parser.parse_args()

	if args.debug:
		logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s %(levelname)s]\t%(message)s')
	else:
		logging.basicConfig(level = logging.INFO, format = '[%(asctime)s %(levelname)s]\t%(message)s')

	if args.tracefile is False and args.interface is False:
		logging.error('No se ha especificado interfaz ni fichero')
		parser.print_help()
		sys.exit(-1)

	signal.signal(signal.SIGINT, signal_handler)

	errbuf = bytearray()
	handle = None
	pdumper_noip = None
	pdumper_rest = None
	dumper_desc = None
	
	# 1. Abrir la interfaz especificada para captura o la traza (Diferenciación de flujo)
	if args.interface:
		handle = pcap_open_live(args.interface, ETH_FRAME_MAX, NO_PROMISC, TO_MS, errbuf)
		if handle is None:
			logging.error('Error al abrir interfaz: {}'.format(errbuf))
			sys.exit(-1)
			
		# Configuración de los ficheros de volcado de tráfico
		fecha = int(time.time())
		dumper_desc = pcap_open_dead(DLT_EN10MB, ETH_FRAME_MAX)
		
		nombre_noip = f"capturaNOIP.{args.interface}.{fecha}.pcap"
		nombre_rest = f"captura.{args.interface}.{fecha}.pcap"
		
		pdumper_noip = pcap_dump_open(dumper_desc, nombre_noip)
		pdumper_rest = pcap_dump_open(dumper_desc, nombre_rest)
		
	elif args.tracefile:
		handle = pcap_open_offline(args.tracefile, errbuf)
		if handle is None:
			logging.error('Error al abrir traza: {}'.format(errbuf))
			sys.exit(-1)
	
	# Gestionar el límite de paquetes por parámetro
	npkts = args.npkts if args.npkts is not None else -1
	
	# 2. Bucle principal (Flujo único)
	ret = pcap_loop(handle, npkts, procesa_paquete, None)
	
	if ret == -1:
		logging.error('Error al capturar un paquete')
	elif ret == -2:
		logging.debug('pcap_breakloop() llamado')
	elif ret == 0:
		logging.debug('No mas paquetes o limite superado')
		
	logging.info('{} paquetes procesados'.format(num_paquete))
	
	# Mostrar la diferencia temporal total exigida
	if num_paquete >= 2 and primer_ts is not None and ultimo_ts is not None:
		diferencia = ultimo_ts - primer_ts
		logging.info('Diferencia de tiempo entre el último y primer paquete: {:.6f} segundos'.format(diferencia))
	else:
		logging.info('Diferencia de tiempo entre el último y primer paquete: 0 segundos')

	# Limpiar memoria y cerrar descriptores
	if pdumper_noip:
		pcap_dump_close(pdumper_noip)
	if pdumper_rest:
		pcap_dump_close(pdumper_rest)
	if dumper_desc:
		pcap_close(dumper_desc)
		
	if handle:
		pcap_close(handle)