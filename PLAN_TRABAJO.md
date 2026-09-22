# Plan de Trabajo – Práctica 1: Búsqueda en IA
## Laboratorio de Inteligencia Artificial – Curso 2026-2027

> **Autores:** Raul Matellano, Jorge Palomino  
> **Grupo:** *(rellenar número de grupo de laboratorio)*  
> **Pareja nº:** *(rellenar identificador de pareja)*

---

## 📋 Resumen de la Práctica

La práctica consiste en implementar algoritmos de búsqueda clásica y con adversarios
aplicados al juego **Reversi (Othello)**. Se divide en dos partes bien diferenciadas:

| Parte | Contenido | Fichero(s) a modificar |
|-------|-----------|------------------------|
| **Parte A** | Árbol de juego + BFS + DFS + A* + 3 heurísticas | `search.py` |
| **Parte B** | Minimax con poda Alfa-Beta + heurísticas del torneo | `strategy.py` + fichero nuevo del torneo |

**Entrega final:** martes 20 o jueves 22 de octubre (antes de la clase de prácticas) — mediante Moodle.

---

## 📅 Calendario y Plazos

```
Sep 15 ─── Sep 21 ─────── Sep 28 ──── Oct 7 ──── Oct 14 ──── Oct 21 ─── Oct 20-22
   │            │              │          │           │           │            │
[Inicio]   [Semana 2]     [Semana 3]  [TORNEO 1] [TORNEO 2] [TORNEO 3]  [ENTREGA]
 Parte A        │           Parte B    20:00h      20:00h     20:00h    Moodle zip
BFS/DFS   A* + heurísticas  Minimax
                              Alfa-Beta
```

### Plazos concretos

| Fecha | Tarea | Tipo |
|-------|-------|------|
| **21 sep** | Terminar Parte A completa | ✅ Recomendado por el enunciado |
| **7 oct — 20:00h** | Subir heurísticas al sistema web — Torneo 1 | ⚠️ **Obligatorio** |
| **14 oct — 20:00h** | Subir heurísticas — Torneo 2 (≥1 distinta al Torneo 1) | ⚠️ **Obligatorio** |
| **21 oct — 20:00h** | Subir heurísticas finales — Torneo 3 | ⚠️ **Obligatorio** |
| **20-22 oct** | Entrega completa por Moodle (zip con código + memoria PDF) | ⚠️ **Obligatorio** |

> ⚠️ La no entrega en Torneo 1 o Torneo 2 puntúa como 0 en ese torneo (penalización directa).

---

## 🗂️ Estructura de Ficheros del Proyecto

```
juegos/
│
│── game.py                          ← NO tocar (lógica general del juego)
│── reversi.py                       ← NO tocar (lógica específica de Reversi)
│── tictactoe.py                     ← NO tocar (útil para depurar minimax)
│── simple_game_tree.py              ← NO tocar (árbol de juego sencillo)
│── tournament.py                    ← NO tocar (infraestructura del torneo)
│── heuristic.py                     ← NO tocar (heurística base ya implementada)
│── util.py                          ← NO tocar (Stack, Queue, PriorityQueue)
│
│── search.py                        ← ✏️  MODIFICAR — Parte A
│── strategy.py                      ← ✏️  MODIFICAR — Parte B (Alfa-Beta)
│── p1_gggg_mm_apellido1_apellido2.py ← ✏️  RENOMBRAR Y COMPLETAR — heurísticas torneo
│
│── demo_reversi.py                  ← Para hacer pruebas (se puede modificar)
│── demo_tictactoe.py                ← Útil para depurar minimax en juego más simple
│── demo_simple_game_tree.py         ← Útil para entender la estructura del árbol
│── demo_tournament.py               ← Para probar torneos locales
│
└── folder_strat/                    ← Carpeta para cargar estrategias externas (torneo)
```

### Nombre final del fichero del torneo
```
p1_GGGG_MM_Matellano_Palomino.py
```
*(reemplazar GGGG y MM con los valores reales del grupo y pareja)*

---

## 📐 Directrices de Código (aplicar siempre)

Estas normas aplican a **todo el código que escribamos**:

1. **Cabecera en cada fichero modificado**, al principio del todo:
   ```python
   # Autores: Raul Matellano, Jorge Palomino
   # Grupo de prácticas: GGGG  Pareja: MM
   # Descripción breve de qué hace este fichero
   ```

2. **Comentario antes de cada función que implementemos**, explicando:
   - Qué recibe
   - Qué devuelve
   - Por qué se hace de esa manera (la idea detrás)

3. **Comentarios dentro del cuerpo** de cada bloque lógico relevante.
   - No comentar línea a línea, sino por bloques de lógica.
   - Ejemplo: "# Comprobamos si ya hemos visitado este estado para no procesar duplicados"

4. **Código simple y directo:**
   - Preferir bucles `for` y `if` normales.
   - Evitar construcciones muy compactas o avanzadas de Python (como lambdas anidadas o comprensiones de lista con condiciones complejas).
   - Usar nombres de variables descriptivos.

5. **No modificar** los ficheros marcados como "NO tocar" salvo que el enunciado lo indique explícitamente.

---

## 🔷 PARTE A — Búsqueda No Informada e Informada

**Semanas 1 y 2: 15–21 de septiembre**  
**Fichero a modificar: `search.py`**

El fichero ya tiene la estructura creada. Hay que completar los huecos marcados con `"YOUR CODE HERE"`.

---

### A.1.1 — Generación del Árbol de Juego

**Qué está ya implementado:**
- La clase `CornerReversiState` con los métodos del juego (movimientos legales, resultado de un movimiento, etc.) — pero faltan 3 huecos dentro de ella.
- La función `build_game_tree(search_problem, max_depth)` — hay que completarla.
- En el `main` ya hay un bucle que llama a `build_game_tree` con profundidades 1, 2, 3 y 4 e imprime las estadísticas.

**Qué hay que completar:**

*Dentro de `CornerReversiState`:*
- `legalMoves()` → devolver la lista de movimientos válidos para el jugador actual.
- `result(move)` → dos huecos: actualizar el color de las fichas capturadas y devolver el nuevo estado.

*La función `build_game_tree`:*
- Recibe un problema de búsqueda y una profundidad máxima.
- Debe generar recursivamente el árbol de juego y acumular estadísticas: número de nodos, hojas, profundidad máxima, suma de ramificación y nodos internos.
- Devuelve el nodo raíz y el diccionario `stats`.

**Preguntas del enunciado a responder (en la memoria):**
- **Pregunta 1.1:** ¿Cómo crece el número de nodos al aumentar la profundidad? Rellenar tabla con los datos del `main`.
- **Pregunta 1.2:** ¿Es viable explorar todo el árbol completo de Reversi? Razonar en base al factor de ramificación.

**Proceso de trabajo recomendado:**
1. Entender primero `CornerReversiState` leyendo sus métodos.
2. Completar `legalMoves()` y `result()` — son imprescindibles para todo lo demás.
3. Probar con `demo_simple_game_tree.py` antes de pasar a Reversi.
4. Implementar `build_game_tree` y ejecutar el `main` para ver las estadísticas.
5. Anotar los resultados en una tabla para la memoria.

---

### A.1.2 — Búsqueda en Profundidad (DFS) y en Anchura (BFS)

**Qué está ya implementado:**
- `depthFirstSearch` tiene el esqueleto completo con 4 huecos marcados.
- `breadthFirstSearch` solo tiene la firma — hay que implementarla desde cero.
- `util.py` ya tiene las estructuras de datos `Stack` y `Queue` listas para usar.
- El `main` ya llama a ambas funciones y mide el tiempo.

**Qué devuelve cada función de búsqueda:**
```python
return num_visited, path   # num_visited: nodos visitados, path: lista de acciones
```
Si no se encuentra solución → `return num_visited, None`

**Huecos de `depthFirstSearch` que hay que completar:**
1. Estado inicial que se mete en la pila.
2. Cómo indexar el estado actual a partir del elemento sacado de la pila.
3. Qué devolver cuando se alcanza el objetivo.
4. Cómo construir el nuevo camino al expandir un sucesor.

**`breadthFirstSearch` hay que escribirla entera**, siguiendo el mismo esquema que DFS pero con una cola (`util.Queue`) en lugar de una pila.

**Preguntas del enunciado a responder (en la memoria):**
- **Pregunta 1.3:** ¿Qué diferencias hay entre BFS y DFS al explorar árboles de juego?
- **Pregunta 1.4:** ¿Cuál de los dos requiere más memoria? ¿Por qué?
- **Pregunta 1.5:** Si cada hoja tuviera una puntuación fija, ¿cuál de los dos encontraría mejor la jugada óptima?

**Proceso de trabajo recomendado:**
1. Completar DFS primero (tiene más estructura ya dada).
2. Implementar BFS siguiendo el mismo esquema pero cambiando la estructura de datos.
3. Ejecutar el `main` en el mismo tablero con ambos métodos.
4. Guardar los resultados (nodos visitados, tiempo, longitud del camino) en una tabla.

---

### A.2 — Búsqueda Informada (A*)

**Qué está ya implementado:**
- `nullHeuristic` — devuelve siempre 0 (heurística trivial).
- `simpleHeuristic` — devuelve el número de fichas en el tablero.
- `heuristic1`, `heuristic2`, `heuristic3` — solo la firma, hay que implementarlas.
- `aStarSearch` — solo la firma, hay que implementarla completa.
- `util.py` tiene `PriorityQueue` lista para usar en A*.
- El `main` ya llama a A* con cada heurística y mide el tiempo.

**Qué hay que implementar:**

*`aStarSearch(search_problem, heuristic)`*  
Recibe el problema y una heurística como argumento.  
Devuelve `(num_visited, path)` igual que BFS/DFS.  
Se basa en una cola de prioridad donde la prioridad de cada nodo es: **coste del camino hasta aquí + estimación de la heurística**.

*3 funciones heurísticas (`heuristic1`, `heuristic2`, `heuristic3`)*  
Reciben un estado y opcionalmente el problema. Devuelven un número (estimación del coste hasta el objetivo).  
Hay que diseñarlas con complejidad creciente (ver ideas más abajo).

**Ideas para las 3 heurísticas de Parte A** *(sobre el problema de alcanzar una esquina)*:
- **heuristic1 (simple):** distancia mínima de alguna ficha propia a la esquina más cercana disponible.
- **heuristic2 (media):** distancia + penalización por fichas enemigas bloqueando el camino.
- **heuristic3 (avanzada):** combinar distancia a esquinas con número de movimientos legales disponibles.

> ⚠️ Estas heurísticas son para el **problema de búsqueda clásica de la Parte A** (encontrar una esquina), no para el torneo de la Parte B.

**Preguntas del enunciado a responder (en la memoria):**
- **Pregunta 1.6:** Definir las 3 heurísticas e implementarlas.
- **Pregunta 1.7:** Comparar A* con BFS y DFS: ¿qué ocurre con el número de nodos y el tiempo?
- **Pregunta 1.8:** ¿Puede la heurística equivocarse? ¿Qué consecuencias tiene para la búsqueda?

**Proceso de trabajo recomendado:**
1. Implementar A* primero usando `nullHeuristic` (equivale a BFS con coste uniforme).
2. Verificar que da el mismo resultado que BFS antes de pasar a heurísticas propias.
3. Diseñar e implementar las 3 heurísticas de menor a mayor complejidad.
4. Ejecutar el `main` y rellenar la tabla comparativa para la memoria.

---

## 🔶 PARTE B — Búsqueda con Adversarios

**Semanas 3–5: 28 de septiembre – 12 de octubre**  
**Ficheros: `strategy.py` (Alfa-Beta) y fichero nuevo para el torneo**

---

### B.1 — Minimax con Poda Alfa-Beta

**Qué está ya implementado:**
- La clase `MinimaxStrategy` completa y funcional — es el minimax **sin** poda.
  - `_min_value` y `_max_value`: la recursión que alterna entre minimizar y maximizar.
  - Ya gestiona: fin de juego, profundidad máxima, heurística, verbose, timeouts.
- La clase `MinimaxAlphaBetaStrategy` tiene el `__init__` y `next_move` creados, pero `next_move` solo devuelve `None` — hay que implementarlo.

**Qué hay que implementar:**  
Dentro de `MinimaxAlphaBetaStrategy.next_move`, añadir las funciones internas `_min_value` y `_max_value` con poda alfa-beta. Se deben seguir la misma estructura que las de `MinimaxStrategy` pero añadiendo los parámetros `alpha` y `beta`.

La diferencia clave respecto a minimax puro:
- En `_max_value`: si el valor del sucesor ≥ beta → cortar (no explorar más ramas).
- En `_min_value`: si el valor del sucesor ≤ alpha → cortar.
- Actualizar alpha y beta a medida que se recorren los sucesores.

El fichero ya incluye (comentado) un snippet de verbose con alpha y beta que hay que usar al implementar.

**Proceso de trabajo recomendado:**
1. Leer `MinimaxStrategy` línea a línea para entender perfectamente cómo funciona.
2. Probar `MinimaxStrategy` jugando una partida en TicTacToe (`demo_tictactoe.py`) con `verbose=2` para ver los valores que se calculan.
3. Implementar Alfa-Beta copiando la estructura de Minimax y añadiendo los parámetros y las condiciones de corte.
4. Comparar el número de nodos explorados entre ambos en el mismo tablero de prueba (resultado debe ser idéntico, nodos mucho menores).
5. Sustituir `MinimaxStrategy` por `MinimaxAlphaBetaStrategy` en `demo_tournament.py` para ahorrar tiempo en los torneos.

---

### B.2 — Funciones Heurísticas para el Torneo

**Fichero a crear:** `p1_GGGG_MM_Matellano_Palomino.py`  
*(copiar y renombrar `p1_gggg_mm_apellido1_apellido2.py`)*

**Estructura obligatoria** (ya viene en la plantilla):
```python
from game import TwoPlayerGameState
from tournament import StudentHeuristic

class MiHeuristica(StudentHeuristic):
    def get_name(self) -> str:
        return "nombre_que_aparece_en_torneo"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Devuelve un número: mayor = más favorable para el jugador actual
        ...
```

**Máximo 3 clases** (el torneo solo usa 3 aunque haya más).  
Hay que decidir al final cuáles son las 3 mejores antes de la entrega.

**Restricciones importantes:**
- ❌ No llamar a funciones del sistema.
- ❌ No manipular estructuras internas del juego.
- ✅ Debe ser eficiente: no tardar más de 10× el tiempo de la heurística trivial.
- ✅ Probar siempre con profundidad máxima de minimax ≤ 4 (como en el torneo real).
- ✅ Probar con tablero 8x8 en configuración estándar Y con obstáculos en B1, H2, A7, G8.

**Plan iterativo de diseño de heurísticas (siguiendo los torneos):**

#### Iteración 1 — Para el Torneo 1 (antes del 7 de octubre)
- **Heurística básica:** diferencia de fichas propias menos fichas del rival.
- Objetivo: tener algo funcional que suba al sistema y verificar que el fichero se carga bien.
- Es mejor que random pero sin más complejidad por ahora.

#### Iteración 2 — Para el Torneo 2 (antes del 14 de octubre)
- **Heurística con esquinas:** las esquinas son posiciones inamovibles una vez capturadas.
  - Dar mucho valor a controlar las 4 esquinas del tablero.
  - Penalizar fuertemente estar en las celdas justo al lado de una esquina (facilitan que el rival la tome).
- Debe ser **diferente** a la del Torneo 1 (requisito del enunciado).
- Usar los torneos internos (tokens disponibles) para medir su rendimiento.

#### Iteración 3 — Para el Torneo 3 (antes del 21 de octubre)
- **Heurística combinada y refinada** en base a los resultados de los torneos anteriores.
- Posibles métricas adicionales a explorar:
  - **Movilidad:** número de movimientos disponibles para nosotros versus el rival.
  - **Estabilidad:** fichas que ya no pueden ser capturadas (esquinas + bordes completos).
  - **Paridad:** en los últimos turnos, quien mueve último tiene ventaja.
- Combinar métricas con pesos y ajustar esos pesos según los resultados.

---

## 📄 Memoria (máx. 8 páginas / 2500 palabras)

La memoria se entrega en PDF junto al código. Debe incluir:

### 1. Funciones de búsqueda (Parte A)
- Tablas con resultados: nodos visitados, tiempo de ejecución, longitud del camino.
  - Comparativa BFS vs DFS.
  - Comparativa A* con las 3 heurísticas vs BFS/DFS.
- Respuestas razonadas a las preguntas 1.1 – 1.8.
- Los razonamientos deben ser **generales** (no basarse en un solo tablero).

### 2. Minimax con Alfa-Beta (Parte B.1)
- Descripción del algoritmo implementado.
- Tabla comparando nodos explorados: Minimax vs Alfa-Beta en el mismo estado.
- Un ejemplo ilustrativo de cómo actúa la poda.

### 3. Documentación del diseño de la heurística (Parte B.2) — 1 punto
- **a)** Revisión de trabajos previos sobre estrategias de Reversi — referencias en formato APA.
- **b)** Descripción del proceso de diseño: ¿cómo se evaluaron las heurísticas? ¿Qué torneos internos se usaron? ¿Cómo evolucionaron entre torneos?
- **c)** Descripción detallada de la heurística enviada finalmente.
- **d)** Otra información relevante.

> 💡 Las referencias APA se obtienen fácilmente desde Google Scholar → botón "Citar" → formato APA.

---

## 🏆 Sistema de Puntuación

| Apartado | Puntos | Detalles |
|----------|--------|----------|
| Árbol de juego + DFS | 0.25 | Parte A — `build_game_tree` + `depthFirstSearch` |
| BFS | 0.50 | Parte A — `breadthFirstSearch` |
| A* + heurísticas (×3) | 1.25 | Parte A — `aStarSearch` + `heuristic1/2/3` |
| Torneo de heurísticas | 3.00 | Parte B — ranking + calidad de heurísticas |
| Memoria | 5.25 | Preguntas, análisis, documentación de heurísticas |
| **TOTAL** | **10** | |

**Torneo — cómo se calcula la nota (1.5 puntos del torneo general):**

| Nota obtenida | Percentil en el ranking |
|---------------|-------------------------|
| 150% (1.5 pts) | Percentil ≥ 90 |
| 100% (1.0 pts) | 50 ≤ Percentil < 90 |
| 75% (0.75 pts) | 10 ≤ Percentil < 50 |
| 50% (0.5 pts) | Percentil < 10 |

**Peso de cada torneo sobre la nota del torneo general:** 15% (T1) · 35% (T2) · 50% (T3)

---

## 📦 Entrega Final

**Nombre del zip:** `p1_GGGG_MM_Matellano_Palomino.zip`

Contenido obligatorio:
```
p1_GGGG_MM_Matellano_Palomino.zip
├── search.py                              ← Parte A implementada (cabecera con autores)
├── strategy.py                            ← Parte B: Alfa-Beta implementado (cabecera con autores)
├── p1_GGGG_MM_Matellano_Palomino.py       ← Heurísticas del torneo (cabecera con autores)
├── memoria.pdf                            ← Memoria (máx. 8 pág. / 2500 palabras)
└── README.txt                             ← Solo si hay ficheros adicionales
```

> ⚠️ Poner nombres y grupo en **todos** los ficheros enviados.

---

## ✅ Checklist de Seguimiento

### Parte A — `search.py`
- [ ] Leer y entender el fichero completo (`CornerReversiState`, problemas, main)
- [ ] Completar `legalMoves()` en `CornerReversiState`
- [ ] Completar `result()` en `CornerReversiState` (2 huecos)
- [ ] Implementar `build_game_tree`
- [ ] Probar árbol con `demo_simple_game_tree.py` (tablero más pequeño)
- [ ] Ejecutar main con profundidades 1, 2, 3, 4 y anotar estadísticas → Pregunta 1.1 y 1.2
- [ ] Completar los 4 huecos de `depthFirstSearch`
- [ ] Implementar `breadthFirstSearch` desde cero
- [ ] Comparar DFS vs BFS en el mismo tablero → Preguntas 1.3, 1.4, 1.5
- [ ] Implementar `aStarSearch`
- [ ] Implementar `heuristic1`, `heuristic2`, `heuristic3`
- [ ] Comparar A* (×3 heurísticas) vs BFS/DFS → Preguntas 1.6, 1.7, 1.8

### Parte B — `strategy.py` y fichero torneo
- [ ] Leer `MinimaxStrategy` completo y entender la lógica de `_min_value` / `_max_value`
- [ ] Probar `MinimaxStrategy` en TicTacToe con `verbose=2`
- [ ] Implementar `MinimaxAlphaBetaStrategy` (funciones `_min_value` y `_max_value` con poda)
- [ ] Comparar Minimax vs Alfa-Beta (mismos resultados, menos nodos explorados)
- [ ] Renombrar plantilla del torneo a `p1_GGGG_MM_Matellano_Palomino.py`
- [ ] Añadir cabecera de autores al fichero del torneo
- [ ] Implementar Heurística 1 (diferencia de fichas)
- [ ] Probar heurística 1 en torneo local con `demo_tournament.py`
- [ ] **→ Subir al sistema web antes del 7 de oct — TORNEO 1** ⚠️
- [ ] Implementar Heurística 2 (esquinas + bordes)
- [ ] Ejecutar torneo interno con tokens para medir rendimiento
- [ ] **→ Subir al sistema web antes del 14 de oct — TORNEO 2** ⚠️
- [ ] Analizar resultados de torneos internos y ajustar métricas
- [ ] Implementar Heurística 3 (combinación refinada)
- [ ] **→ Subir al sistema web antes del 21 de oct — TORNEO 3** ⚠️

### Memoria
- [ ] Tabla de resultados BFS vs DFS (nodos, tiempo, longitud del camino)
- [ ] Tabla de resultados A* con las 3 heurísticas
- [ ] Responder preguntas 1.1 a 1.8 con razonamientos generales
- [ ] Apartado Minimax + Alfa-Beta con comparativa de nodos
- [ ] Búsqueda bibliográfica sobre estrategias de Reversi (referencias APA)
- [ ] Descripción del proceso de diseño de heurísticas
- [ ] Descripción de la heurística final enviada
- [ ] Verificar: ≤ 8 páginas y ≤ 2500 palabras
- [ ] Poner nombres y grupo en la memoria

### Entrega final
- [ ] Cabecera con autores en `search.py`, `strategy.py` y fichero del torneo
- [ ] Crear `README.txt` si se incluyen ficheros adicionales
- [ ] Crear zip con el nombre correcto
- [ ] **→ Subir a Moodle antes del 20-22 de octubre** ⚠️
