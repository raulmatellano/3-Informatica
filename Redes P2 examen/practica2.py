'''
	practica2.py
	Programa principal que ejecuta resoluciones ARP y mensajería Ethernet.
	Autor: Jorge Palomino y Raul Matellano
	2020 EPS-UAM
'''

# ==============================================================================
# RESUMEN GENERAL Y GUÍA DE ESTUDIO: practica2.py (PUNTO DE ENTRADA Y CONSOLA)
# ==============================================================================
# Este archivo es el programa principal (driver). No implementa la lógica de los
# protocolos directamente, sino que coordina e interactúa con:
#   - ethernet.py: Nivel 2 de enlace.
#   - ethmsg.py:   Nivel de mensajería sobre Ethernet.
#   - arp.py:      Nivel de resolución de direcciones.
#
# ------------------------------------------------------------------------------
# ORDEN ESTRICTO DE INICIALIZACIÓN (¡PREGUNTA CLÁSICA DE EXAMEN!):
# ------------------------------------------------------------------------------
#   PASO 1: startEthernetLevel(interface)  [ethernet.py]
#           - Abre la interfaz de red con pcap_open_live en modo promiscuo.
#           - Lee y almacena la MAC local con getHwAddr.
#           - Arranca el hilo receptor rxThread con pcap_loop.
#           - ¡DEBE IR PRIMERO! Si no se inicializa Ethernet, ningún otro protocolo
#             podrá enviar ni recibir paquetes.
#
#   PASO 2: initEthMsg(interface)          [ethmsg.py]
#           - Registra en EthernetProtocols el callback process_ethMsg_frame para 0x0AA0.
#
#   PASO 3: initARP(interface)             [arp.py]
#           - Registra en EthernetProtocols el callback process_arp_frame para 0x0806.
#           - Obtiene y guarda myIP y myMAC.
#           - Ejecuta el ARP Gratuito inicial llamando a ARPResolution(myIP).
#             (Si otro equipo contesta, aborta con -1 por IP duplicada).
#
# ------------------------------------------------------------------------------
# COMANDOS DE LA CONSOLA INTERACTIVA:
# ------------------------------------------------------------------------------
#   - 'a <IP>'    : Llama a ARPResolution(ip) y muestra la MAC asociada en la LAN.
#   - 'm <texto>' : Llama a sendEthMsg(mensaje) y lo envía en broadcast a toda la LAN.
#   - 'p'         : Llama a printCache() y muestra el contenido actual de la caché ARP.
#   - 'g'         : Obtiene nuestra IP y envía un ARP gratuito bajo demanda.
#   - 'h'         : Muestra el menú de ayuda.
#   - 'q' / Ctrl+C: Sale del bucle y llama a stopEthernetLevel() para liberar recursos.
# ==============================================================================

from ethernet import *   # startEthernetLevel, stopEthernetLevel, sendEthernetFrame
from arp import *         # initARP, ARPResolution, printCache, getIP
from ethmsg import *      # initEthMsg, sendEthMsg
import sys
import binascii
import signal
import argparse
import struct
from argparse import RawTextHelpFormatter
import time
import logging
import socket

def printHelp():
	''' Imprime por consola la lista de comandos disponibles en la aplicación '''
	print ( "Ayuda Consola:\n")
	print ( "\tm <mensaje> : Envia un mensaje utilizando protocolo Ethernet\n")
	print ( "\ta <direccionIP> : Solicita ARP Request sobre la IP indicada\n")
	print ( "\tp : Imprime cache ARP\n")
	print ( "\th : Muestra la ayuda\n")
	print ( "\tg : Envia un ARP gratuito\n")
	print ( "\tq : Salir del programa\n")


if __name__ == "__main__":
	global pdumper,args,handle,el,stop

	# ==========================================================================
	# 1. PARSEO DE PARÁMETROS DE LÍNEA DE COMANDOS
	# ==========================================================================
	#   --itf <interfaz>: OBLIGATORIO. Nombre de la interfaz a abrir (ej: --itf eth0).
	#   --debug:          OPCIONAL. Activa trazas detalladas de logging.
	parser = argparse.ArgumentParser(description='Esta práctica ejecuta resoluciones ARP. Dada una dirección IP devuelve cual es la MAC asociada en la LAN actual',
	formatter_class=RawTextHelpFormatter)
	parser.add_argument('--itf', dest='interface', default=False,help='Interfaz a abrir')
	parser.add_argument('--debug', dest='debug', default=False, action='store_true',help='Activar Debug messages')
	args = parser.parse_args()

	# Configuración del nivel de logs según la opción --debug
	if args.debug:
		logging.basicConfig(level = logging.DEBUG, format = '[%(asctime)s %(levelname)s]\t%(message)s')
	else:
		logging.basicConfig(level = logging.INFO, format = '[%(asctime)s %(levelname)s]\t%(message)s')

	# Si el usuario no especificó --itf, no se puede continuar
	if args.interface is False:
		logging.error('No se ha especificado interfaz')
		parser.print_help()
		sys.exit(-1)

	
	# ==========================================================================
	# 2. SECUENCIA DE INICIALIZACIÓN POR CAPAS
	# ==========================================================================
	
	# PASO 1: Inicializamos el nivel Ethernet en la interfaz especificada
	# (abre pcap_open_live, obtiene MAC local y arranca rxThread con pcap_loop)
	if (startEthernetLevel(args.interface) != 0):
		logging.error('Ethernet no inicializado')
		sys.exit(-1)

	# PASO 2: Inicializamos el protocolo EthMsg
	# (registra el callback process_ethMsg_frame para tramas con Ethertype 0x0AA0)
	initEthMsg(args.interface)

	# PASO 3: Inicializamos el nivel ARP
	# (registra callback para 0x0806, guarda myIP/myMAC y comprueba IP duplicada con ARP gratuito)
	if initARP(args.interface) == -1:
		logging.error('ARP no inicializado')
		stopEthernetLevel() # Limpieza de seguridad antes de salir
		sys.exit(-1)
		
	# ==========================================================================
	# 3. BUCLE PRINCIPAL DE CONSOLA INTERACTIVA
	# ==========================================================================
	print("Introduce la orden correspondiente:\n")
	
	while True:
		try:
			comando = input(">> ")

			# COMANDO 'q': Salir de la consola
			if comando == "q":
				print("Saliendo de la consola.")
				break  # Sale del bucle para ejecutar la parada limpia

			# COMANDO 'p': Imprimir la tabla de caché ARP
			elif comando == 'p':
				printCache()

			# COMANDO 'h': Mostrar ayuda
			elif comando == 'h':
				printHelp()

			# COMANDO 'a <IP>': Resolución ARP de una IP destino
			elif comando.startswith("a "):
				ipstr = comando.split(" ")[1]
				print(f"Enviando solicitud ARP a {ipstr}...")
				try:
					# Conversión de IP texto "X.X.X.X" -> 4 bytes -> entero de 32 bits big-endian
					# socket.inet_aton convierte a bytes; struct.unpack('!I') lo pasa a entero
					ip = struct.unpack('!I', socket.inet_aton(ipstr))[0]

					# Invocamos la función de resolución ARP
					ret = ARPResolution(ip)

					# Si hubo respuesta, formateamos los 6 bytes de la MAC a "XX:XX:XX:XX:XX:XX"
					if ret is not None:
						print(':'.join(['{:02X}'.format(b) for b in ret]))
					else:
						print('Dirección no encontrada\n')
				except OSError:
					# Error si la cadena introducida no tiene formato de IP válido
					print('Formato de IP incorrecta\n')
			
			# COMANDO 'm <texto>': Envío de mensaje por Ethernet en difusión
			elif comando.startswith("m "):
				partes = comando.split(" ")
				mensaje = " ".join(partes[1:]) # Recompone el mensaje tras quitar el comando 'm '
				print(f"Enviando mensaje de {len(mensaje)} Bytes: {mensaje}")
				sendEthMsg(mensaje)

			# COMANDO 'g': Envío de ARP Gratuito bajo demanda
			elif comando == 'g':
				print("Enviando ARP gratuito")
				mi_ip = getIP(args.interface)  # Obtenemos nuestra propia IP
				ARPResolution(mi_ip)           # Emitimos petición preguntando por nuestra IP

			else:
				print("Comando no reconocido. 'h' para ayuda.\n")

		except KeyboardInterrupt:
			# Captura Ctrl+C para salir ordenadamente sin volcado de excepciones
			print('\n')
			break

	# ==========================================================================
	# 4. CIERRE Y LIBERACIÓN LIMPIA DE RECURSOS
	# ==========================================================================
	logging.info('Cerrando ....')
	
	# Paramos el nivel Ethernet (interrumpe el hilo rxThread con pcap_breakloop y cierra el handle pcap)
	if (stopEthernetLevel() != 0):
		logging.error('Parando nivel Ethernet')
		sys.exit(-1)