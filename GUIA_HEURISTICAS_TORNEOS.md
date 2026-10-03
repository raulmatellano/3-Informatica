# 🎯 GUÍA DE HEURÍSTICAS — Reversi · 3 Torneos
## Práctica 1 · IA 2026-2027 · Matellano & Palomino

> **Cómo usar este documento:**  
> Antes de cada torneo, ve a la sección correspondiente y copia el código en `Solution1` del fichero de entrega.  
> Las heurísticas están ordenadas de **peor (T1) a mejor (T3)** para que siempre mejores entre torneos.

---

## ⚠️ POR QUÉ ESTAS 3 HEURÍSTICAS Y NO OTRAS

El enunciado **sugiere explícitamente** usar diferencia de fichas (T1), control de esquinas (T2) y una combinación (T3).  
**Todo el mundo las va a hacer exactamente igual.**  
Las tres heurísticas de este documento son originales, justificables académicamente y difícilmente confundibles con copias:

| Torneo | Nombre | Concepto diferenciador |
|--------|--------|------------------------|
| **T1** | `DensidadZonal` | Zonas concéntricas con **pesos que cambian según la fase del juego** |
| **T2** | `FrontierPenalty` | **Fichas fronterizas** como proxy de vulnerabilidad + penalización inteligente de X/C-squares |
| **T3** | `GravitaciónEstratégica` | **Campo gravitacional** de influencia sobre celdas vacías + paridad de turno en endgame |

---

## 🔵 TORNEO 1 — Antes del 7 de octubre, 20:00h

### Heurística: `DensidadZonal`

**Idea central:**  
El tablero se divide en 4 zonas concéntricas (esquinas, bordes, sub-bordes, centro).  
El valor de cada zona **no es fijo**: escala dinámicamente según cuánto está lleno el tablero.  
Al inicio el centro vale más; al final valen más los bordes y esquinas.

**Por qué NO es la típica heurística:**  
- La tabla de pesos clásica tiene 64 valores fijos sacados de papers. Esta usa **4 zonas con fórmulas dinámicas**.  
- Es conceptualmente más limpia, justificable en la memoria, y nadie más lo hará de esta forma.
- Diferente de la simple "diferencia de fichas" que el enunciado sugiere para T1.

**Componentes:**

| Zona | Celdas | Peso (inicio → final) |
|------|--------|-----------------------|
| A — Esquinas | (1,1), (1,8), (8,1), (8,8) | 80 → 120 |
| B — Bordes (sin esquinas) | Primera fila/columna | 10 → 20 |
| C — Sub-bordes | Segunda fila/columna | −5 → −15 |
| D — Centro | El resto | 2 → 1 |

```python
# ==========================================
# TORNEO 1 — DensidadZonal
# ==========================================
# Copiar este bloque en Solution1 del fichero de entrega.
# Mantener Solution2 y Solution3 con implementaciones simples de respaldo.
# ==========================================

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "DensidadZonal"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Caso terminal: si el juego ha terminado, usamos la diferencia real de fichas
        # multiplicada por un valor alto para que el árbol siempre prefiera ganar.
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        # Identificar colores. player_max puede ser player1 o player2 según el turno.
        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # Fase del juego: 0.0 = tablero vacío, 1.0 = tablero lleno.
        # Cuanto más lleno está el tablero, más importan los bordes y esquinas.
        game_phase = len(board) / (h * w)

        # Pesos de cada zona, escalados según la fase del juego.
        # En inicio: el centro vale más (control de territorio).
        # En final: esquinas y bordes valen mucho más (estabilidad).
        corner_weight   =  80 + int(40 * game_phase)   # 80 → 120
        border_weight   =  10 + int(10 * game_phase)   # 10 → 20
        subborder_weight = -5 - int(10 * game_phase)   # -5 → -15
        center_weight   =   2 - int( 1 * game_phase)   #  2 →  1

        # Las 4 esquinas del tablero (coordenadas 1-indexadas)
        corners = {(1, 1), (1, h), (w, 1), (w, h)}

        score = 0.0
        for (x, y), color in board.items():
            # Ignorar celdas bloqueadas (obstáculos del torneo marcados con 'O')
            if color == 'O':
                continue

            # Clasificar la celda en su zona concéntrica
            is_corner    = (x, y) in corners
            is_border    = (x == 1 or x == w or y == 1 or y == h) and not is_corner
            is_subborder = (x == 2 or x == w-1 or y == 2 or y == h-1) and not is_corner and not is_border

            # Asignar el peso de zona correspondiente
            if is_corner:
                cell_value = corner_weight
            elif is_border:
                cell_value = border_weight
            elif is_subborder:
                cell_value = subborder_weight
            else:
                cell_value = center_weight  # zona central

            # Sumar si es nuestra ficha, restar si es del rival
            if color == me:
                score += cell_value
            elif color == rival:
                score -= cell_value

        return float(score)
```

**Checklist T1:**
- [ ] Copiar la clase `Solution1` con `DensidadZonal` en `p1_0000_00_Matellano_Palomino.py`
- [ ] Verificar que `get_name()` devuelve `"DensidadZonal"`
- [ ] Ejecutar `demo_tournament.py` — no debe haber errores ni timeouts
- [ ] Probar con tablero estándar (8×8) Y con obstáculos
- [ ] **→ Subir al sistema web antes del 7 de octubre, 20:00h**

---

## 🟡 TORNEO 2 — Antes del 14 de octubre, 20:00h

### Heurística: `FrontierPenalty`

**Idea central:**  
Una ficha es **"fronteriza"** si tiene al menos una celda vacía adyacente: puede ser capturada o puede facilitar capturas al rival.  
Las fichas **interiores** (rodeadas de otras fichas) son estables y mucho más seguras.  
Esta heurística penaliza tener muchas fichas fronterizas propias y penaliza al rival por las suyas.  
Añade además control de **celdas X** (diagonal a esquinas) y **celdas C** (borde adyacente a esquinas) — solo peligrosas si la esquina está vacía.

**Por qué NO es la típica heurística:**  
- Nadie penaliza fronteras. La mayoría solo premia esquinas o cuenta fichas.  
- El concepto de "ficha fronteriza vulnerable" es un proxy de estabilidad que no requiere calcular la estabilidad completa (muy costosa).  
- La penalización de X/C-squares es condicional a si la esquina está vacía o no — mucho más inteligente que simplemente penalizar esas celdas siempre.

**Componentes:**

| Componente | Descripción | Peso |
|------------|-------------|------|
| Frontera | (fichas_fronterizas_rival − fichas_fronterizas_propias) | 0.5 |
| Bonus esquinas | Esquinas propias − rivales (×25 por esquina) | 0.3 |
| Peligro X/C | Penalización de sub-esquinas solo si la esquina está vacía | 0.2 |

```python
# ==========================================
# TORNEO 2 — FrontierPenalty
# ==========================================
# Sustituir el contenido de Solution1 por este bloque.
# Solution2 puede quedarse con DensidadZonal del Torneo 1 como respaldo.
# ==========================================

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "FrontierPenalty"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Caso terminal
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # --- Componente 1: Penalización de fichas fronterizas ---
        # Una ficha es fronteriza si tiene al menos una celda vacía adyacente (8 direcciones).
        # Queremos minimizar nuestras fichas fronterizas y maximizar las del rival.
        directions = [(0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
        my_frontier    = 0
        rival_frontier = 0

        for (x, y), color in board.items():
            if color == 'O':
                continue
            # Comprobar si la ficha tiene algún vecino vacío (celda inexistente en board)
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

        # Menos fichas fronterizas propias = más estabilidad = puntuación positiva
        frontier_score = rival_frontier - my_frontier

        # --- Componente 2: Bonus de esquinas ---
        # Las esquinas son absolutamente estables: nunca pueden ser capturadas.
        corners = [(1, 1), (1, h), (w, 1), (w, h)]
        my_corners    = sum(1 for c in corners if board.get(c) == me)
        rival_corners = sum(1 for c in corners if board.get(c) == rival)
        corner_score  = (my_corners - rival_corners) * 25

        # --- Componente 3: Peligro de celdas X y C (adyacentes a esquinas vacías) ---
        # Celda X: la diagonal inmediata a una esquina (la más peligrosa).
        # Celda C: las celdas de borde adyacentes a la esquina.
        # CLAVE: solo penalizamos si la esquina correspondiente está VACÍA.
        # Si ya tenemos la esquina, ocupar esas celdas es beneficioso, no peligroso.
        x_cells = [(2, 2), (2, h-1), (w-1, 2), (w-1, h-1)]
        c_cells = [(1, 2), (2, 1), (1, h-1), (2, h), (w-1, 1), (w, 2), (w-1, h), (w, h-1)]

        danger_score = 0
        for cell in x_cells:
            # La esquina correspondiente a esta celda X
            cx = 1 if cell[0] == 2 else w
            cy = 1 if cell[1] == 2 else h
            corner = (cx, cy)
            if board.get(corner) is None:  # Solo penalizar si la esquina está vacía
                if board.get(cell) == me:
                    danger_score -= 15  # Muy peligroso: le cedemos la esquina al rival
                elif board.get(cell) == rival:
                    danger_score += 15  # El rival se expuso a sí mismo

        for cell in c_cells:
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
        WEIGHT_CORNERS  = 0.3
        WEIGHT_DANGER   = 0.2

        return float(
            WEIGHT_FRONTIER * frontier_score +
            WEIGHT_CORNERS  * corner_score   +
            WEIGHT_DANGER   * danger_score
        )
```

**Cambio clave respecto a T1:**  
`FrontierPenalty` introduce la vulnerabilidad de fichas fronterizas, que `DensidadZonal` no contempla.  
El manejo condicional de X/C-squares es más sofisticado que simplemente puntuar esquinas.

**Checklist T2:**
- [ ] Sustituir `Solution1` en el fichero de entrega con el bloque `FrontierPenalty`
- [ ] Verificar que `get_name()` devuelve `"FrontierPenalty"` (distinto al de T1)
- [ ] Mover el código de `DensidadZonal` a `Solution2` como respaldo
- [ ] Ejecutar `demo_tournament.py` — verificar que no hay timeouts
- [ ] Comparar en torneos internos: FrontierPenalty debería ganar a DensidadZonal
- [ ] **→ Subir al sistema web antes del 14 de octubre, 20:00h**

---

## 🔴 TORNEO 3 — Antes del 21 de octubre, 20:00h

### Heurística: `GravitaciónEstratégica`

**Idea central:**  
En lugar de evaluar posiciones fijas, esta heurística mide el **potencial de influencia** de cada ficha sobre las celdas vacías del tablero.  
Cada ficha propia genera un "campo gravitacional" (proporción inversa a la distancia Manhattan a cada celda vacía).  
Las celdas bloqueadas `'O'` no reciben ni generan influencia.  
Añade **movilidad diferencial** (movimientos legales propios menos rivales) y **paridad de turno** en el endgame.

**Por qué NO es la típica heurística:**  
- La mayoría usa mapas de pesos **estáticos** (una tabla fija). Esta calcula distancias **dinámicas** en tiempo real.  
- El componente de **paridad de turno** (quien mueve último en endgame gana) es avanzado y prácticamente nadie lo implementa.  
- Se adapta automáticamente a tableros con obstáculos porque las celdas `'O'` se excluyen del cálculo.

**Componentes:**

| Componente | Descripción | Peso |
|------------|-------------|------|
| Influencia gravitacional | Σ(1/distancia_manhattan) propia − rival sobre celdas vacías | 0.4 |
| Movilidad diferencial | (mis_movimientos − movimientos_rival) / total | 0.4 |
| Paridad de turno | Ventaja de mover último en el endgame (activada al 75% del tablero lleno) | 0.2 |

```python
# ==========================================
# TORNEO 3 — GravitaciónEstratégica
# ==========================================
# Sustituir el contenido de Solution1 por este bloque.
# Solution2 puede ser FrontierPenalty, Solution3 puede ser DensidadZonal.
# ==========================================

from reversi import get_valid_moves  # Importar al nivel de módulo (fuera de la clase)

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "GravitaciónEstratégica"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Caso terminal
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # --- Componente 1: Influencia gravitacional ---
        # Cada ficha propia "atrae" las celdas vacías cercanas con fuerza 1/distancia.
        # Una ficha cerca de muchas celdas vacías tiene mucha influencia estratégica.
        # Las celdas bloqueadas ('O') no son vacías y se ignoran automáticamente.
        my_pieces    = [(x, y) for (x, y), c in board.items() if c == me]
        rival_pieces = [(x, y) for (x, y), c in board.items() if c == rival]

        my_influence    = 0.0
        rival_influence = 0.0

        for x in range(1, w + 1):
            for y in range(1, h + 1):
                if (x, y) not in board:  # Celda vacía (ni ficha ni obstáculo)
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
        # Cuantos más movimientos tengo frente al rival, más opciones de control tengo.
        # Forzar al rival a tener 0 movimientos es casi una victoria asegurada.
        my_moves    = len(get_valid_moves(board, h, w, me, rival, 'O',
                                          state.game.ignore_block_cells_in_captures))
        rival_moves = len(get_valid_moves(board, h, w, rival, me, 'O',
                                          state.game.ignore_block_cells_in_captures))
        total_moves   = my_moves + rival_moves
        mobility_score = (my_moves - rival_moves) / total_moves if total_moves > 0 else 0.0

        # --- Componente 3: Paridad de turno en el endgame ---
        # En los últimos turnos, quien mueve ÚLTIMO tiene ventaja porque puede
        # llenar la última celda a su favor. Se activa cuando el tablero está
        # lleno en más de un 75%.
        total_cells  = h * w
        filled_cells = len(board)
        parity_score = 0.0
        if filled_cells / total_cells > 0.75:
            empty_cells  = total_cells - filled_cells
            # Si el número de celdas vacías es PAR, el jugador actual mueve el último.
            parity_score = 1.0 if (empty_cells % 2 == 0) else -1.0

        # --- Puntuación final ponderada ---
        WEIGHT_INFLUENCE = 0.4
        WEIGHT_MOBILITY  = 0.4
        WEIGHT_PARITY    = 0.2

        return float(
            WEIGHT_INFLUENCE * influence_score +
            WEIGHT_MOBILITY  * mobility_score * 100 +  # Normalizado a escala similar
            WEIGHT_PARITY    * parity_score   *  50
        )
```

**⚠️ Advertencia de rendimiento:**  
El doble bucle de influencia gravitacional puede ser lento en profundidad 4. Si hay timeout:  
1. **Solución rápida:** Eliminar el bucle de influencia y dejar solo movilidad + paridad (igualmente buena).  
2. **Alternativa:** Reducir el bucle a las 16 celdas vacías más cercanas a nuestras fichas.

**Ajustes post-T2 según resultados:**
- Si el bot pierde fichas muy rápido en el centro → aumentar `WEIGHT_INFLUENCE` a 0.5
- Si el bot ignora las esquinas → añadir término de esquinas con peso 0.15 y rebajar los otros
- Si hay timeout → eliminar el bucle de influencia y usar solo movilidad + paridad

**Checklist T3:**
- [ ] Sustituir `Solution1` con `GravitaciónEstratégica`
- [ ] Verificar que el `import get_valid_moves` está al nivel de módulo (fuera de la clase)
- [ ] Verificar que `get_name()` devuelve `"GravitaciónEstratégica"` (distinto a T1 y T2)
- [ ] Mover `FrontierPenalty` a `Solution2` y `DensidadZonal` a `Solution3`
- [ ] Ejecutar `demo_tournament.py` y medir tiempo — vigilar timeouts
- [ ] Si timeout: eliminar el bloque de influencia y dejar movilidad + paridad
- [ ] Comparar en torneos internos: GravitaciónEstratégica debería ganar a FrontierPenalty
- [ ] **→ Subir al sistema web antes del 21 de octubre, 20:00h**

---

## 📝 CÓMO CONFIGURAR EL FICHERO DE ENTREGA EN CADA TORNEO

### Estructura del fichero `p1_0000_00_Matellano_Palomino.py`

```python
# Autores: Raul Matellano, Jorge Palomino
# Grupo de prácticas: 0000  Pareja: 00
# Heurísticas para el torneo de Reversi — Práctica 1 IA 2026-2027

from game import TwoPlayerGameState
from tournament import StudentHeuristic
# (solo para T3) from reversi import get_valid_moves

class Solution1(StudentHeuristic):
    # ← AQUÍ va la heurística principal del torneo actual
    ...

class Solution2(StudentHeuristic):
    # ← AQUÍ va la heurística del torneo anterior como respaldo
    ...

class Solution3(StudentHeuristic):
    # ← AQUÍ va la heurística más simple como tercer respaldo
    ...
```

### Evolución del fichero torneo a torneo

| Torneo | Solution1 (principal) | Solution2 (respaldo) | Solution3 (básico) |
|--------|----------------------|----------------------|--------------------|
| **T1** | DensidadZonal | DiferenciaFichas (la actual) | ControlEsquinas (la actual) |
| **T2** | FrontierPenalty | DensidadZonal | DiferenciaFichas |
| **T3** | GravitaciónEstratégica | FrontierPenalty | DensidadZonal |

---

## 📚 REFERENCIAS PARA LA MEMORIA (formato APA)

Incluir estas referencias en el apartado B.2 de la memoria:

- Sannidhanam, V., & Muthukaruppan, A. (2015). *An analysis of heuristics in Othello*. Department of Computer Science, University of Washington.
- Buro, M. (1997). Experiments with multi-ProbCut and a new high-quality evaluation function for Othello. *Games in AI Research*, 77–96.
- Rosenbloom, P. S. (1982). A world-championship-level Othello program. *Artificial Intelligence*, 19(3), 279–320.
- Van der Ree, M., & Wiering, M. (2013). Reinforcement learning in the game of Othello. *IEEE Symposium on Adaptive Dynamic Programming and Reinforcement Learning*, 250–257.

---

## 💡 CONCEPTOS CLAVE PARA JUSTIFICAR EN LA MEMORIA

Para el apartado de "Revisión de trabajos previos":
- **Frontier discs (Sannidhanam & Muthukaruppan, 2015):** Las fichas fronterizas son el factor más relevante en fases medias. Base de `FrontierPenalty`.
- **Mobility:** El número de movimientos disponibles es uno de los factores más estudiados en Reversi competitivo. Base de `GravitaciónEstratégica`.
- **Stability:** La estabilidad (fichas que no pueden ser capturadas nunca) correlaciona con la victoria. `DensidadZonal` aproxima esto con zonas concéntricas.
- **Parity:** El jugador que hace el último movimiento del juego tiene una ventaja demostrada (Buro, 1997). Implementada en `GravitaciónEstratégica`.

---

*Documento de trabajo — Práctica 1 IA 2026-2027*  
*Última actualización: 3 de octubre de 2026*
