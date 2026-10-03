# 🎯 Estrategia de Heurísticas — Reversi (Othello)
## Práctica 1 · Torneo de IA · Matellano & Palomino

> **Documento de diseño estratégico**: guía para evolucionar las heurísticas a lo largo de los 3 torneos.  
> Cada torneo usa la solución del nivel correspondiente; se va de peor a mejor.

---

## 📌 CONTEXTO Y ANÁLISIS DEL PROYECTO

### ¿Qué busca el torneo?
El torneo evalúa la calidad de la **función de evaluación heurística** que se le pasa al algoritmo **Minimax con poda Alfa-Beta**. Esa función recibe un estado del tablero de Reversi (8×8) y devuelve un número: cuanto mayor, más favorable para el jugador MAX.

### Restricciones del torneo
- Máximo **3 clases** (`Solution1`, `Solution2`, `Solution3`)
- La función debe ser **eficiente** (≤ 10× el tiempo de la heurística trivial)
- Profundidad máxima del árbol Minimax en el torneo: **4 niveles**
- Se juega en tablero 8×8 con configuración estándar **Y** con obstáculos (celdas bloqueadas `'O'`)

### Por qué las heurísticas actuales son demasiado comunes
Las 3 heurísticas del fichero actual (`DiferenciaFichas`, `ControlEsquinas`, `EsquinasYFichas`) son exactamente las que el enunciado **sugiere explícitamente** en el PLAN_TRABAJO.md (líneas 292-310). Todo el mundo las va a hacer. Necesitamos algo diferente.

---

## 🏆 TOP 3 DE HEURÍSTICAS PROPUESTAS

> **Orden**: de mejor a peor (la #1 es la más potente y la más compleja).  
> **Estrategia de entrega**: usar la #3 en T1 (la más débil), la #2 en T2, y la #1 en T3.

---

## 🥇 HEURÍSTICA 1 — «GravitaciónEstratégica» *(mejor, para TORNEO 3)*

### Concepto
En lugar de evaluar posiciones concretas (esquinas, bordes), esta heurística mide el **potencial de influencia** de cada ficha sobre el tablero usando una función de distancia ponderada. Cada ficha propia genera un "campo gravitacional" que se atenúa con la distancia, y las fichas enemigas actúan como repulsores.

La clave diferenciadora es que **el peso de cada celda del tablero no es fijo** (como en los mapas de pesos clásicos), sino que se **calcula dinámicamente** en función de:
1. La fase del juego (inicio, medio, final)
2. Las fichas bloqueadas (`'O'`) que alteran el mapa estratégico
3. La movilidad diferencial (número de movimientos disponibles)

### Componentes

| Componente | Descripción | Peso inicial |
|------------|-------------|-------------|
| **Influencia gravitacional** | Suma de (1/distancia_manhattan) a cada ficha propia vs enemiga | 0.4 |
| **Movilidad diferencial** | Mis movimientos legales − movimientos legales del rival | 0.4 |
| **Paridad de turno** | En la fase final (>48 fichas), quién mueve último tiene ventaja | 0.2 |

### Por qué no es común
- La mayoría usa mapas de pesos **estáticos** (una tabla fija de valores por celda). Esta usa distancias **dinámicas** calculadas en tiempo real.
- El componente de **paridad** (turno ventajoso en endgame) es avanzado y prácticamente nadie lo implementa.
- Se **adapta a tableros con obstáculos** porque las celdas bloqueadas no generan ni reciben influencia.

### Implementación (para TORNEO 3)

```python
class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "GravitaciónEstratégica"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # --- Caso terminal ---
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # --- Componente 1: Influencia gravitacional ---
        # Cada ficha propia "atrae" las celdas vacías cercanas.
        # Usamos la inversa de la distancia Manhattan como medida de influencia.
        # Así, una ficha en una esquina influye más en las celdas adyacentes
        # que una ficha en el centro.
        my_influence = 0.0
        rival_influence = 0.0

        my_pieces = [(x, y) for (x, y), c in board.items() if c == me]
        rival_pieces = [(x, y) for (x, y), c in board.items() if c == rival]

        # Calculamos para cada celda vacía del tablero cuánta influencia acumula
        for x in range(1, w + 1):
            for y in range(1, h + 1):
                if (x, y) not in board:  # Celda vacía (posible movimiento futuro)
                    for (px, py) in my_pieces:
                        dist = abs(x - px) + abs(y - py)
                        if dist > 0:
                            my_influence += 1.0 / dist
                    for (px, py) in rival_pieces:
                        dist = abs(x - px) + abs(y - py)
                        if dist > 0:
                            rival_influence += 1.0 / dist

        influence_score = my_influence - rival_influence

        # --- Componente 2: Movilidad diferencial ---
        # Cuantos más movimientos tengo vs el rival, más opciones tengo
        # para controlar el juego. Forzar al rival a tener 0 movimientos = victoria casi segura.
        from reversi import get_valid_moves
        my_moves = len(get_valid_moves(
            board, h, w, me, rival, 'O', state.game.ignore_block_cells_in_captures
        ))
        rival_moves = len(get_valid_moves(
            board, h, w, rival, me, 'O', state.game.ignore_block_cells_in_captures
        ))
        total_moves = my_moves + rival_moves
        mobility_score = (my_moves - rival_moves) / total_moves if total_moves > 0 else 0

        # --- Componente 3: Paridad de turno (endgame) ---
        # En los últimos movimientos del juego, el jugador que mueve en último lugar
        # tiene ventaja porque puede "llenar" la última celda a su favor.
        # Activamos este componente solo cuando el tablero esté lleno en más de un 75%.
        total_cells = h * w
        filled_cells = len(board)
        parity_score = 0.0
        if filled_cells / total_cells > 0.75:
            # Si el número de celdas vacías es par, el jugador que mueve ahora
            # moverá el último (ventaja). Si es impar, el rival moverá el último.
            empty_cells = total_cells - filled_cells
            # Intentamos saber si somos nosotros quienes tenemos la paridad ventajosa
            parity_score = 1.0 if (empty_cells % 2 == 0) else -1.0

        # --- Puntuación final ponderada ---
        # Pesos ajustados según la importancia de cada componente en Reversi competitivo
        WEIGHT_INFLUENCE = 0.4
        WEIGHT_MOBILITY = 0.4
        WEIGHT_PARITY = 0.2

        return float(
            WEIGHT_INFLUENCE * influence_score +
            WEIGHT_MOBILITY * mobility_score * 100 +  # normalizamos a escala similar
            WEIGHT_PARITY * parity_score * 50
        )
```

---

## 🥈 HEURÍSTICA 2 — «FrontierPenalty» *(media, para TORNEO 2)*

### Concepto
En Reversi, una ficha es **"fronteriza"** si tiene al menos una celda vacía adyacente (en las 8 direcciones). Las fichas fronterizas son **vulnerables**: pueden ser capturadas o pueden facilitar capturas al rival. En cambio, las fichas **interiores** (rodeadas de otras fichas) son más estables.

Esta heurística mide la diferencia de **fichas fronterizas** y **fichas interiores** como proxy de estabilidad, sin necesidad de calcular la estabilidad real (que es costosa computacionalmente).

La intuición: quiero tener **pocas** fichas fronterizas propias y que el **rival** tenga **muchas**.

### Componentes

| Componente | Descripción | Peso |
|------------|-------------|------|
| **Penalización de frontera** | (fichas_fronterizas_rival − fichas_fronterizas_propias) | 0.5 |
| **Bonus de esquinas** | Esquinas capturadas propias vs rivales (×25 por esquina) | 0.3 |
| **Peligro de sub-esquina** | Penaliza las celdas adyacentes a esquinas vacías (celdas "X" y "C") | 0.2 |

### Por qué no es común
- Casi nadie penaliza **fronteras**. La gente premia fichas o esquinas.
- El concepto de "ficha fronteriza peligrosa" es un intermedio entre "diferencia de fichas" (demasiado miope) y "estabilidad completa" (demasiado costosa).
- Las **celdas X y C** (las más peligrosas adyacentes a esquinas) se penalizan explícitamente, lo cual es menos obvio que simplemente premiar esquinas.

### Implementación (para TORNEO 2)

```python
class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "FrontierPenalty"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # --- Caso terminal ---
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # --- Componente 1: Penalización de frontera ---
        # Una ficha es "fronteriza" si tiene al menos una celda vacía adyacente.
        # Las fichas fronterizas son más vulnerables y señalan posiciones inestables.
        # Queremos que el rival tenga más fichas fronterizas que nosotros.
        directions = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]

        my_frontier = 0
        rival_frontier = 0
        for (x, y), color in board.items():
            # Una ficha es fronteriza si tiene al menos una celda vacía adyacente
            is_frontier = any(
                (x + dx, y + dy) not in board
                and 1 <= x + dx <= w
                and 1 <= y + dy <= h
                for dx, dy in directions
            )
            if is_frontier:
                if color == me:
                    my_frontier += 1
                elif color == rival:
                    rival_frontier += 1

        # Queremos minimizar nuestras fichas fronterizas y maximizar las del rival
        frontier_score = rival_frontier - my_frontier

        # --- Componente 2: Bonus de esquinas ---
        # Las esquinas son absolutamente estables (no pueden ser volteadas nunca).
        corners = [
            (1, 1), (1, h), (w, 1), (w, h)
        ]
        my_corners = sum(1 for c in corners if board.get(c) == me)
        rival_corners = sum(1 for c in corners if board.get(c) == rival)
        corner_score = (my_corners - rival_corners) * 25

        # --- Componente 3: Peligro de sub-esquinas (celdas X y C) ---
        # Las celdas inmediatamente adyacentes a las esquinas vacías son peligrosas:
        # si las ocupamos antes de tener la esquina, le facilitamos la esquina al rival.
        # Celdas "X": diagonales de esquinas = (2,2), (2,h-1), (w-1,2), (w-1,h-1)
        # Celdas "C": bordes adyacentes a esquinas = (1,2),(2,1), etc.
        x_cells = [(2, 2), (2, h-1), (w-1, 2), (w-1, h-1)]
        c_cells = [(1, 2), (2, 1), (1, h-1), (2, h), (w-1, 1), (w, 2), (w-1, h), (w, h-1)]

        danger_score = 0
        for cell in x_cells:
            corner = None
            # Determinamos qué esquina le corresponde a esta celda X
            cx = 1 if cell[0] == 2 else w
            cy = 1 if cell[1] == 2 else h
            corner = (cx, cy)
            # Solo penalizamos si la esquina adyacente todavía está vacía
            if board.get(corner) is None:
                if board.get(cell) == me:
                    danger_score -= 15  # Muy peligroso: le cedemos la esquina al rival
                elif board.get(cell) == rival:
                    danger_score += 15  # El rival se puso en peligro a sí mismo
        
        for cell in c_cells:
            # Determinar la esquina más cercana a esta celda C
            cx = 1 if cell[0] <= 2 else w
            cy = 1 if cell[1] <= 2 else h
            corner = (cx, cy)
            if board.get(corner) is None:
                if board.get(cell) == me:
                    danger_score -= 7
                elif board.get(cell) == rival:
                    danger_score += 7

        # --- Puntuación final ponderada ---
        WEIGHT_FRONTIER = 0.5
        WEIGHT_CORNERS = 0.3
        WEIGHT_DANGER = 0.2

        return float(
            WEIGHT_FRONTIER * frontier_score +
            WEIGHT_CORNERS * corner_score +
            WEIGHT_DANGER * danger_score
        )
```

---

## 🥉 HEURÍSTICA 3 — «DensidadZonal» *(más débil, para TORNEO 1)*

### Concepto
El tablero de Reversi se divide en **4 zonas concéntricas** con valores distintos:
- **Zona A (esquinas)**: Las 4 esquinas. Valor altísimo.
- **Zona B (bordes)**: Las celdas del borde exterior (excluidas esquinas). Valor alto.
- **Zona C (sub-bordes)**: La segunda fila/columna interior. Valor levemente negativo (peligrosas).
- **Zona D (centro)**: El resto del tablero. Valor neutro o ligeramente positivo.

La **diferenciación clave** es que el valor de cada zona **escala con la fase del juego**. En el inicio, el centro vale más (expandir presencia); en el final, los bordes y esquinas dominan.

A diferencia de un mapa de pesos estático, los **pesos de las zonas se ajustan dinámicamente** según cuántas fichas hay en el tablero.

### Componentes

| Zona | Celdas | Valor base (inicio) | Valor (final) |
|------|--------|---------------------|---------------|
| A — Esquinas | (1,1),(1,8),(8,1),(8,8) | +80 | +120 |
| B — Bordes (sin esquinas) | Primera fila/col | +10 | +20 |
| C — Sub-bordes | Segunda fila/col | −5 | −15 |
| D — Centro | Resto | +2 | +1 |

### Por qué no es común
- La mayoría de mapas de pesos son **estáticos** y con valores ad hoc sacados de papers.
- El **ajuste dinámico por fase del juego** (ratio de fichas sobre el total del tablero) diferencia esta heurística de un simple mapa de valores fijo.
- El concepto de **zonas concéntricas** es más elegante y justificable que una tabla 8×8 hardcodeada celda a celda.

### Implementación (para TORNEO 1)

```python
class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "DensidadZonal"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # --- Caso terminal ---
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # --- Fase del juego: cuánto está lleno el tablero (0.0 = vacío, 1.0 = lleno) ---
        # Esto nos permite ajustar los pesos según si estamos en inicio, medio o final.
        game_phase = len(board) / (h * w)  # Valor entre 0 y 1

        # --- Pesos de zona según la fase del juego ---
        # En el inicio, el centro tiene más valor (control del territorio).
        # En el final, los bordes y esquinas son mucho más valiosos (estabilidad).
        corner_weight = 80 + int(40 * game_phase)    # 80 → 120
        border_weight = 10 + int(10 * game_phase)    # 10 → 20
        subborder_weight = -5 - int(10 * game_phase) # −5 → −15
        center_weight = 2 - int(1 * game_phase)      # 2 → 1

        # --- Clasificación de cada celda del tablero en su zona ---
        corners = {(1, 1), (1, h), (w, 1), (w, h)}

        score = 0.0
        for (x, y), color in board.items():
            # Ignorar celdas bloqueadas (obstáculos del torneo)
            if color == 'O':
                continue

            # Determinar a qué zona pertenece la celda
            is_corner = (x, y) in corners
            is_border = (x == 1 or x == w or y == 1 or y == h) and not is_corner
            is_subborder = (x == 2 or x == w - 1 or y == 2 or y == h - 1) and not is_corner and not is_border
            # El resto es zona central

            # Asignar el peso de zona
            if is_corner:
                cell_value = corner_weight
            elif is_border:
                cell_value = border_weight
            elif is_subborder:
                cell_value = subborder_weight
            else:
                cell_value = center_weight

            # Sumar al score si es nuestra ficha, restar si es del rival
            if color == me:
                score += cell_value
            elif color == rival:
                score -= cell_value

        return float(score)
```

---

## 📅 GUÍA DE ACCIÓN POR TORNEO

### 🔵 TORNEO 1 — Antes del 7 de octubre, 20:00h
**Usar**: `Solution3` (DensidadZonal) como heurística principal

**Instrucciones para el fichero de entrega:**
1. En `p1_0000_00_Matellano_Palomino.py`, sustituir el contenido de `Solution1` con la implementación de `DensidadZonal`.
2. Las otras dos clases (`Solution2` y `Solution3`) pueden quedarse con implementaciones básicas de respaldo o directamente copias simplificadas de la misma lógica con pesos diferentes.
3. El objetivo del Torneo 1 es **estar en el sistema, funcionar correctamente y no quedar últimos**.

**Checklist T1:**
- [ ] Implementar `DensidadZonal` en `Solution1` del fichero de entrega
- [ ] Verificar que el fichero se carga bien con `demo_tournament.py`
- [ ] Verificar que no hay timeouts con profundidad 4 en tablero 8×8
- [ ] Subir al sistema web antes del 7 de octubre, 20:00h

---

### 🟡 TORNEO 2 — Antes del 14 de octubre, 20:00h
**Usar**: `Solution2` (FrontierPenalty) como heurística principal

**Instrucciones de cambio:**
1. Sustituir el contenido de `Solution1` del fichero de entrega con la implementación de `FrontierPenalty`.
2. Asegurarse de que el **nombre en `get_name()`** es diferente al del Torneo 1 (requisito del enunciado: al menos 1 heurística distinta).
3. `Solution2` puede ser `DensidadZonal` como respaldo, `Solution3` puede ser la básica original.

**Cambio clave respecto a T1:**
- `FrontierPenalty` introduce la idea de **vulnerabilidad de fichas fronterizas**, que `DensidadZonal` no contempla.
- El componente de **sub-esquinas (celdas X y C)** es más sofisticado que simplemente puntuar esquinas.

**Checklist T2:**
- [ ] Implementar `FrontierPenalty` en `Solution1`
- [ ] Verificar que `get_name()` devuelve un nombre diferente al de T1
- [ ] Usar los tokens de torneo interno para comparar vs T1
- [ ] Verificar que no hay timeouts (el cálculo de frontera añade algo de coste)
- [ ] Subir al sistema web antes del 14 de octubre, 20:00h

---

### 🔴 TORNEO 3 — Antes del 21 de octubre, 20:00h
**Usar**: `Solution1` (GravitaciónEstratégica) como heurística principal

**Instrucciones de cambio:**
1. Sustituir `Solution1` con `GravitaciónEstratégica`.
2. `Solution2` puede ser `FrontierPenalty` (mantenerla como respaldo potente).
3. `Solution3` puede ser `DensidadZonal` (mantenerla como la más simple/rápida).

**Cambio clave respecto a T2:**
- `GravitaciónEstratégica` añade **movilidad diferencial** (número de movimientos legales), que es uno de los factores más determinantes en Reversi competitivo.
- La **paridad de turno** en endgame es un factor avanzado que los equipos sin investigación previa no implementarán.
- El enfoque de **influencia gravitacional** es único y no trivialmente comparable con mapas de pesos estáticos.

**Ajustes opcionales post-T2:**
Si tras el Torneo 2 ves que `FrontierPenalty` falla en algún escenario específico, puedes ajustar los pesos de `GravitaciónEstratégica` antes de subirlo:
- Si el bot pierde fichas muy rápido en el centro → aumentar `WEIGHT_INFLUENCE` a 0.5
- Si el bot ignora las esquinas → añadir un término de esquinas con peso 0.15 y rebajar los otros
- Si el bot es lento → eliminar el bucle de influencia gravitacional y sustituirlo solo por movilidad

**Checklist T3:**
- [ ] Implementar `GravitaciónEstratégica` en `Solution1`
- [ ] Verificar timing: puede ser más lenta por el doble bucle de influencia (vigilar timeouts)
- [ ] Si hay timeout, simplificar eliminando el bucle de celdas vacías y usando solo las fichas del rival como referencia
- [ ] Usar los tokens para comparar vs T1 y T2
- [ ] Subir al sistema web antes del 21 de octubre, 20:00h

---

## ⚠️ NOTAS IMPORTANTES DE IMPLEMENTACIÓN

### Cómo acceder al rival correctamente
```python
me = state.player_max.label
rival = state.player1.label if me == state.player2.label else state.player2.label
```
Este patrón es el correcto porque `player_max` puede ser player1 o player2 según el turno.

### Cómo acceder al tablero con obstáculos
```python
board = state.board  # Dict: {(x,y): 'B'|'W'|'O'}
# 'B' = negro (player1), 'W' = blanco (player2), 'O' = celda bloqueada
# Las celdas sin clave son celdas vacías (movimientos posibles)
```
Siempre ignorar las celdas con valor `'O'` en los cálculos de fichas.

### Cómo calcular movimientos legales (para T3)
```python
from reversi import get_valid_moves
my_moves = len(get_valid_moves(board, h, w, me, rival, 'O', state.game.ignore_block_cells_in_captures))
```
Esto puede tener un coste computacional relevante. Si hay timeout en profundidad 4, es el primer componente a eliminar.

### Tamaño del tablero
```python
h = state.game.height  # normalmente 8
w = state.game.width   # normalmente 8
```
Nunca hardcodear 8: el código debe funcionar con cualquier tamaño.

---

## 📚 Referencias bibliográficas (para la memoria)

- Sannidhanam, V., & Muthukaruppan, A. (2015). *An analysis of heuristics in Othello*. Department of Computer Science, University of Washington.
- Buro, M. (1997). *Experiments with multi-ProbCut and a new high-quality evaluation function for Othello*. Games in AI Research, 77-96.
- Rosenbloom, P. S. (1982). *A world-championship-level Othello program*. Artificial Intelligence, 19(3), 279-320.
- Van der Ree, M., & Wiering, M. (2013). *Reinforcement learning in the game of Othello*. IEEE Symposium on Adaptive Dynamic Programming and Reinforcement Learning.

---

*Documento generado para la Práctica 1 de Inteligencia Artificial — Curso 2026-2027*  
*Última actualización: 3 de octubre de 2026*
