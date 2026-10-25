# GUÍA COMPLETA DE EXAMEN — Práctica 2: Ethernet y ARP

> **Objetivo**: Tenerlo todo claro para no pillarte en ninguna pregunta tipo test, de flujo de funciones ni de modificación de código.

---

## 1. ARQUITECTURA EN CAPAS (MUY IMPORTANTE)

```
practica2.py   ← Programa principal. Solo usa las APIs de los módulos. NO implementa protocolos.
    │
    ├── ethernet.py  ← Capa base. Maneja pcap, envío/recepción de tramas Ethernet.
    │       └── rc1_pcap.py  ← Wrapper de la librería C libpcap. NO se modifica.
    │
    ├── arp.py       ← Protocolo ARP. Usa ethernet.py para enviar/recibir.
    │
    └── ethmsg.py   ← Protocolo de mensajería. Usa ethernet.py para enviar/recibir.
```

**Regla de oro**: Los protocolos superiores (ARP, EthMsg) **nunca** se llaman entre sí.
Todos pasan por `ethernet.py` para enviar y se registran en él para recibir.

---

## 2. ORDEN DE INICIALIZACIÓN (practica2.py)

```
1. startEthernetLevel(interface)   → ethernet.py: abre pcap, guarda macAddress, arranca rxThread
2. initEthMsg(interface)           → ethmsg.py: registra callback para Ethertype 0x0AA0 (ETHTYPE)
3. initARP(interface)              → arp.py: registra callback para Ethertype 0x0806, guarda myIP/myMAC, ARP gratuito
```

> [!IMPORTANT]
> El nivel Ethernet **SIEMPRE** se inicializa primero. Sin él, los demás no pueden enviar ni registrar callbacks.

---

## 3. FLUJO DE RECEPCIÓN DE TRAMAS (de abajo a arriba)

```
Red física
   ↓
pcap captura la trama
   ↓
pcap_loop() → llama a process_frame()          [ethernet.py]
   ↓
process_frame() → lanza process_Ethernet_frame() en un HILO NUEVO (threading.Thread)
   ↓
process_Ethernet_frame():
   - Lee MAC destino [0:6] y MAC origen [6:12]
   - Descarta si dst != nuestra MAC ni broadcast
   - Lee Ethertype [12:14]
   - Busca en EthernetProtocols[ethertype] → llama al callback registrado
   ↓
Si Ethertype == 0x0806  →  process_arp_frame()    [arp.py]
   ↓
   - Lee opcode [6:8]:
     - opcode==1 → processARPRequest()   (alguien nos pregunta)
     - opcode==2 → processARPReply()     (alguien nos responde)

Si Ethertype == 0x0AA0  →  process_ethMsg_frame()  [ethmsg.py]
   ↓
   - Lee longitud [0:2], mensaje [2:2+longitud]
   - Imprime con timestamp pcap
```

> [!NOTE]
> **¿Por qué hilos?** `process_frame()` lanza un hilo nuevo para `process_Ethernet_frame()`.
> Esto evita bloqueos: si ARP está esperando una respuesta, el pcap_loop puede seguir recibiendo tramas.

---

## 4. FLUJO DE ENVÍO DE TRAMAS (de arriba a abajo)

```
practica2.py:  ARPResolution(ip) / sendEthMsg(msg)
   ↓
arp.py:        sendEthernetFrame(paquete_arp, len, 0x0806, broadcastAddr)
ethmsg.py:     sendEthernetFrame(payload_msg, len, 0x0AA0, broadcast)
   ↓
ethernet.py:   sendEthernetFrame():
               - Ensambla trama: [dstMAC(6)] + [srcMAC(6)] + [etherType(2)] + [data]
               - Comprueba límites: mín 60B (rellena con 0x00), máx 1514B (error)
               - pcap_inject(handle, frame, len)  → envía por la red
```

---

## 5. ESTRUCTURA DE TRAMAS (IMPRESCINDIBLE MEMORIZAR)

### Trama Ethernet completa:
```
[0:6]   MAC destino     (6 bytes)
[6:12]  MAC origen      (6 bytes)
[12:14] Ethertype       (2 bytes, big-endian): 0x0806=ARP, 0x0800=IP, 0x0AA0=EthMsg (0x3003 en versiones previas)
[14:]   Payload         (datos del protocolo superior, SIN cabecera Ethernet)
```

### Payload ARP (data que recibe process_arp_frame, sin la cabecera Ethernet):
```
[0:6]   ARPHeader fijo  = 0x00 0x01 0x08 0x00 0x06 0x04
                          HW=Ethernet, Proto=IPv4, HWlen=6, Protolen=4
[6:8]   Opcode          (2 bytes): 0x0001=Request, 0x0002=Reply
[8:14]  Sender MAC      (6 bytes) ← quien envía
[14:18] Sender IP       (4 bytes) ← IP de quien envía
[18:24] Target MAC      (6 bytes) ← en Request: 00:00:00:00:00:00 (desconocida)
[24:28] Target IP       (4 bytes) ← IP que se busca (Request) / nuestra IP (Reply)
```

### Payload EthMsg (data que recibe process_ethMsg_frame):
```
[0:2]   Longitud del mensaje  (2 bytes, big-endian, '!H')
[2:]    Mensaje en UTF-8
```

---

## 6. VARIABLES GLOBALES CLAVE

### ethernet.py
| Variable | Tipo | Propósito |
|---|---|---|
| `macAddress` | bytes (6B) | Nuestra MAC. Obtenida con `getHwAddr()` en `startEthernetLevel()`. |
| `handle` | pcap_t | Handle de pcap (apuntador a la interfaz abierta). |
| `levelInitialized` | bool | Bandera: True si el nivel Ethernet ya está activo. Evita doble inicialización. |
| `recvThread` | rxThread | El hilo que corre pcap_loop en segundo plano. |
| `EthernetProtocols` | dict | `{ethertype: función_callback}`. Se rellena con `registerEthCallback()`. |
| `broadcastAddr` | bytes | `FF:FF:FF:FF:FF:FF` |

### arp.py
| Variable | Tipo | Propósito |
|---|---|---|
| `myIP` | int (32 bits) | Nuestra IP. Obtenida con `getIP()` en `initARP()`. |
| `myMAC` | bytes (6B) | Nuestra MAC. Obtenida con `getHwAddr()` en `initARP()`. |
| `requestedIP` | int | IP que ARPResolution está tratando de resolver ahora mismo. |
| `resolvedMAC` | bytes | MAC resuelta. La escribe `processARPReply`, la lee `ARPResolution`. |
| `awaitingResponse` | bool | True = estamos esperando respuesta. False = ya la tenemos. |
| `globalLock` | Lock | Protege requestedIP, resolvedMAC y awaitingResponse (acceso concurrente). |
| `cache` | ExpiringDict | Caché ARP. `{IP(int): MAC(bytes)}`. Expira a los 10 segundos. |
| `cacheLock` | Lock | Protege el acceso a la caché (hilo principal + hilo de recepción). |

---

## 7. FUNCIONES Y QUIÉN LLAMA A QUIÉN

### Llamadas de practica2.py (hacia afuera):
- `startEthernetLevel(itf)` → ethernet.py
- `initEthMsg(itf)` → ethmsg.py
- `initARP(itf)` → arp.py
- `printCache()` → arp.py
- `ARPResolution(ip)` → arp.py
- `sendEthMsg(msg)` → ethmsg.py
- `getIP(itf)` → arp.py
- `stopEthernetLevel()` → ethernet.py

### Llamadas de arp.py (hacia ethereum.py):
- `registerEthCallback(process_arp_frame, 0x0806)` → ethernet.py
- `sendEthernetFrame(paquete, len, 0x0806, dst)` → ethernet.py
- `getHwAddr(itf)` → ethernet.py

### Llamadas de ethmsg.py (hacia ethernet.py):
- `registerEthCallback(process_ethMsg_frame, 0x0AA0)` → ethernet.py
- `sendEthernetFrame(trama, len, 0x0AA0, broadcast)` → ethernet.py

### Cadena de recepción (automática, no llamada explícitamente):
`pcap_loop` → `process_frame` → `process_Ethernet_frame` → `[process_arp_frame | process_ethMsg_frame]`

---

## 8. EL ARP GRATUITO (GRATUITOUS ARP)

- Se hace en `initARP()` llamando a `ARPResolution(myIP)` con **nuestra propia IP**.
- Enviamos un ARP Request preguntando "¿quién tiene MI IP?".
- **Si alguien responde**: hay conflicto de IPs → `initARP()` devuelve -1 → salimos con error.
- **Si nadie responde** (None): la IP es libre → inicialización correcta.
- También se puede lanzar manualmente con el comando `g` en practica2.py.

---

## 9. CONCURRENCIA Y LOCKS (PREGUNTA FRECUENTE)

Hay **dos hilos** corriendo a la vez:
1. **Hilo principal** (practica2.py): lee comandos del teclado, llama a ARPResolution.
2. **rxThread** (ethernet.py): corre pcap_loop, recibe tramas, llama a processARPReply.

Los dos acceden a `requestedIP`, `resolvedMAC` y `awaitingResponse` → **condición de carrera**.

**Solución**: `globalLock` (Lock de Python). Siempre que se lean/escriban estas variables se usa `with globalLock:`.

Igual con la caché: se usa `cacheLock` por separado para no mezclar protecciones.

---

## 10. SIMULACROS — PATRÓN DE MODIFICACIÓN

> [!TIP]
> La clave de todos los simulacros es saber **en qué archivo** y **en qué función** modificar. Aquí el resumen:

| Simulacro | ¿Qué cambiar? | ¿Dónde? | Concepto clave |
|---|---|---|---|
| **1 - Firewall MAC** | Añadir filtro por MAC origen | `process_Ethernet_frame` (ethernet.py) | Bloquear antes de que llegue a ARP o EthMsg |
| **2 - Mensajes unicast** | Cambiar broadcast por MAC destino | `sendEthMsg` (ethmsg.py) + nuevo comando en practica2.py | Pasar MAC como parámetro con valor por defecto |
| **3 - Magic Number** | Añadir 2 bytes fijos (0xFACE) al inicio | `sendEthMsg` y `process_ethMsg_frame` (ethmsg.py) | struct '!HH' para empaquetar/desempaquetar dos shorts |
| **4 - VLAN 802.1Q** | Insertar etiqueta VLAN en la cabecera | `sendEthernetFrame` y `process_Ethernet_frame` (ethernet.py) | 4 bytes extra entre MAC origen y Ethertype real |
| **5 - Checksum trailer** | Añadir 1 byte al final del payload | `sendEthMsg` y `process_ethMsg_frame` (ethmsg.py) | El índice del checksum es `2 + longitud` |
| **6 - Ping-Pong** | Auto-responder si el mensaje es "!PING" | `process_ethMsg_frame` (ethmsg.py) | Inspeccionar texto después de decodificar, llamar a `sendEthMsg("!PONG")` |
| **Examen - Prioridad** | Añadir 1 byte de prioridad al inicio | `sendEthMsg` y `process_ethMsg_frame` (ethmsg.py) | struct '!BH' (1 byte + 2 bytes) |

---

## 11. REFERENCIA RÁPIDA DE struct.pack/unpack

```python
# EMPAQUETAR (datos → bytes para enviar):
struct.pack('!H',  valor)          # 1 unsigned short (2 bytes), big-endian
struct.pack('!I',  valor)          # 1 unsigned int   (4 bytes), big-endian
struct.pack('!B',  valor)          # 1 unsigned byte  (1 byte)
struct.pack('!HH', val1, val2)     # 2 unsigned shorts (4 bytes)
struct.pack('!BH', val1, val2)     # 1 byte + 1 short (3 bytes)
struct.pack('!HHH',v1, v2, v3)     # 3 unsigned shorts (6 bytes) → para VLAN

# DESEMPAQUETAR (bytes recibidos → datos):
val, = struct.unpack('!H',  data[0:2])     # ← la coma es necesaria con un solo valor
val  = struct.unpack('!H',  data[0:2])[0] # ← alternativa con [0]
v1, v2 = struct.unpack('!HH', data[0:4])
v1, v2 = struct.unpack('!BH', data[0:3])

# '!' = big-endian (network byte order) — SIEMPRE en redes
# 'H' = unsigned short = 2 bytes
# 'I' = unsigned int   = 4 bytes
# 'B' = unsigned byte  = 1 byte
```

---

## 12. REFERENCIA RÁPIDA DE CONVERSIONES MAC/IP

```python
# MAC bytes → string legible "XX:XX:XX:XX:XX:XX"
':'.join(['{:02X}'.format(b) for b in mac_bytes])

# String MAC "00:11:22:33:44:55" → bytes
bytes.fromhex("00:11:22:33:44:55".replace(':', ''))

# IP string "192.168.1.1" → entero 32 bits
struct.unpack('!I', socket.inet_aton("192.168.1.1"))[0]

# Entero 32 bits → IP string "192.168.1.1"
socket.inet_ntoa(struct.pack('!I', ip_int))

# Entero 32 bits → bytes (4B, para poner en paquete ARP)
struct.pack('!I', ip_int)
```

---

## 13. ANÁLISIS DETALLADO DE CADA SIMULACRO

### SIMULACRO 1 — Firewall MAC (ethernet.py → process_Ethernet_frame)

**Concepto**: El nivel Ethernet es el "conserje". Es el único punto donde se puede bloquear tráfico antes de que llegue a ARP o EthMsg.

**Modificación**: Añadir justo **después de extraer srcMac** y **antes del filtro de destino**:

```python
mac_atacante = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55])
if origen == mac_atacante:   # 'origen' = data[6:12]
    return  # Descartamos silenciosamente
```

**¿Por qué aquí?** Porque si lo hicieras en `process_arp_frame` o `process_ethMsg_frame`, solo bloquearías ARP o EthMsg, pero no ambos. En Ethernet bloqueas **todo** de una vez.

---

### SIMULACRO 2 — Mensajes Unicast (ethmsg.py + practica2.py)

**Concepto**: EthMsg siempre envía en broadcast. Para envío privado, hay que pasar una MAC destino.

**Modificación 1** — `sendEthMsg` en ethmsg.py:
```python
# Añadimos parámetro dst_mac con valor por defecto = broadcast
def sendEthMsg(message, dst_mac=broadcast) -> bytes:
    ...
    sendEthernetFrame(trama, len(trama), ETHTYPE, dst_mac)  # usa dst_mac en vez de broadcast
```

**Modificación 2** — Nuevo comando 'u' en practica2.py:
```python
elif comando.startswith("u "):
    partes = comando.split(" ")
    mac_str = partes[1]                           # "00:11:22:33:44:55"
    mensaje = " ".join(partes[2:])
    mac_bytes = bytes.fromhex(mac_str.replace(':', ''))
    sendEthMsg(mensaje, dst_mac=mac_bytes)
```

---

### SIMULACRO 3 — Magic Number 0xFACE (ethmsg.py)

**Concepto**: Añadir 2 bytes fijos de firma al inicio para verificar autenticidad.

**Nueva estructura del payload EthMsg**:
```
[0:2]  Magic Number (2B) = 0xFACE  ← nuevo
[2:4]  Longitud del mensaje (2B)    ← antes estaba en [0:2]
[4:]   Mensaje
```

**Envío**:
```python
cabecera = struct.pack('!HH', 0xFACE, longitud)  # 2B magic + 2B longitud
payload = cabecera + mensaje
```

**Recepción**:
```python
if len(data) < 4: return
magic, longitud = struct.unpack('!HH', data[0:4])
if magic != 0xFACE: return  # Descartar
texto = data[4:4+longitud]
```

---

### SIMULACRO 4 — VLAN 802.1Q (ethernet.py)

**Concepto**: Las VLAN añaden 4 bytes entre MAC origen y Ethertype.

**Nueva estructura de la cabecera Ethernet con VLAN**:
```
[0:6]   MAC destino
[6:12]  MAC origen
[12:14] 0x8100  ← indica que hay etiqueta VLAN
[14:16] VLAN ID (ej: 10)
[16:18] Ethertype real (0x0806, 0x3003, etc.)
[18:]   Payload
```

**Envío** (`sendEthernetFrame`):
```python
# struct '!HHH' = 3 unsigned shorts = 6 bytes: [0x8100][VLAN_ID][etherType]
frame = dstMac + macAddress + struct.pack('!HHH', 0x8100, 10, etherType) + data
```

**Recepción** (`process_Ethernet_frame`):
```python
campo = struct.unpack('!H', data[12:14])[0]
if campo == 0x8100:      # Trae VLAN
    ethertype = struct.unpack('!H', data[16:18])[0]
    payload = data[18:]
else:                    # Sin VLAN (normal)
    ethertype = campo
    payload = data[14:]
```

---

### SIMULACRO 5 — Checksum al final (ethmsg.py)

**Concepto**: Añadir 1 byte de control al FINAL del payload (trailer), valor fijo 0xFF.

**Nueva estructura**:
```
[0:2]         Longitud (2B)
[2:2+longitud] Mensaje
[2+longitud]   Checksum = 0xFF  ← nuevo, al final
```

**Envío**:
```python
byte_final = struct.pack('!B', 0xFF)
payload = struct.pack('!H', longitud) + mensaje + byte_final
```

**Recepción**:
```python
longitud = struct.unpack('!H', data[0:2])[0]
texto = data[2:2+longitud]
idx_cs = 2 + longitud                           # índice del checksum varía con la longitud
if len(data) < idx_cs + 1: return
checksum = struct.unpack('!B', data[idx_cs:idx_cs+1])[0]
if checksum != 0xFF: return  # Descartamos
```

---

### SIMULACRO 6 — Auto-respuesta Ping-Pong (ethmsg.py)

**Concepto**: Inspeccionar el mensaje recibido y actuar como bot automático.

**Modificación** en `process_ethMsg_frame` (después de decodificar el texto):
```python
if mensaje == "!PING":
    sendEthMsg("!PONG")    # Respondemos en broadcast
else:
    print(f"[...] {mac}: {mensaje}")   # Comportamiento normal
```

> [!NOTE]
> `sendEthMsg` se puede llamar desde dentro de `process_ethMsg_frame` porque están en el mismo módulo.
> Como la recepción corre en un hilo separado, el envío no bloquea nada.

---

### SIMULACRO EXAMEN — Byte de Prioridad (ethmsg.py)

**Concepto**: Añadir 1 byte de prioridad al INICIO del payload (antes de la longitud).

**Nueva estructura**:
```
[0]    Prioridad (1B) = 5     ← nuevo, al inicio
[1:3]  Longitud (2B)
[3:]   Mensaje
```

**Envío**:
```python
cabecera = struct.pack('!BH', 5, longitud)  # '!BH' = 1 byte + 2 bytes = 3 bytes
payload = cabecera + mensaje
```

**Recepción**:
```python
if len(data) < 3: return
prioridad, longitud = struct.unpack('!BH', data[0:3])
texto = data[3:3+longitud]
print(f"[...] {mac}: P{prioridad} - {texto_legible}")
```

---

## 14. ETHERTYPES USADOS EN LA PRÁCTICA

| Ethertype | Protocolo | Dónde se registra |
|---|---|---|
| `0x0806` | ARP | `initARP()` en arp.py |
| `0x0800` | IPv4 | Referencia en enunciado (IP estándar) |
| `0x0AA0` | **EthMsg (Oficial Enunciado)** | `initEthMsg()` en ethmsg.py (¡Exigido en enunciado actual!) |
| `0x3003` | EthMsg (Simulacros / versiones previas) | Documentado para simulacros antiguos |
| `0x8100` | VLAN 802.1Q | Simulacro 4 |

> [!WARNING]
> Consulta el informe detallado de trampas del enunciado en: [TRAMPAS_Y_CRITERIOS_PROFESORES_P2.md](file:///home/raul/.gemini/antigravity-ide/brain/0d0a59c3-f4aa-42ae-a146-7dfb418e1061/TRAMPAS_Y_CRITERIOS_PROFESORES_P2.md) para conocer las 10 trampas detectadas que podrían provocar un suspenso o eliminación en la evaluación.

---

## 15. rc1_pcap.py — FUNCIONES CLAVE (NO SE MODIFICA)

| Función | Qué hace |
|---|---|
| `pcap_open_live(iface, snaplen, promisc, to_ms, errbuf)` | Abre la interfaz de red para captura. Devuelve un `handle`. |
| `pcap_loop(handle, cnt, callback, user)` | Bucle infinito (cnt=-1). Llama a `callback` por cada trama. |
| `pcap_inject(handle, buf, size)` | Envía bytes directamente por la interfaz. |
| `pcap_breakloop(handle)` | Para el bucle de `pcap_loop`. Usado en `rxThread.stop()`. |
| `pcap_close(handle)` | Cierra el handle y libera recursos. |

Las clases `pcap_pkthdr` y `timeval` definen la estructura de la cabecera de cada paquete capturado (campos: `ts.tv_sec`, `ts.tv_usec`, `len`, `caplen`).

