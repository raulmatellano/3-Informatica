# Autores: Raul Matellano, Jorge Palomino
# Grupo de prácticas: 0000  Pareja: 00
# Descripción: Heurísticas para el torneo de Reversi — Práctica 1 IA 2026-2027.
#   - Solution1 (DensidadZonal): heurística principal para el Torneo 1.
#       Divide el tablero en 4 zonas concéntricas (esquinas, bordes, sub-bordes,
#       centro) cuyos pesos escalan dinámicamente según la fase del juego.
#       Evita tanto el conteo miope de fichas como los mapas de pesos estáticos.
#   - Solution2 (ControlEsquinas): heurística de respaldo. Premia las esquinas
#       capturadas, que son posiciones absolutamente estables en Reversi.
#   - Solution3 (EsquinasYFichas): heurística de respaldo adicional. Combina
#       control de esquinas con diferencia de fichas para desempatar.

from game import TwoPlayerGameState
from tournament import StudentHeuristic


# ===========================================================================
# HEURÍSTICA PRINCIPAL — TORNEO 1
# Nombre: DensidadZonal
# ===========================================================================
# Concepto:
#   El tablero se divide en 4 zonas concéntricas con importancia diferente:
#     - Zona A (esquinas): Las 4 esquinas. Inviolables una vez capturadas.
#     - Zona B (bordes):   Celdas del borde exterior (excluidas esquinas).
#     - Zona C (sub-borde): Segunda fila/columna interior. Peligrosas: facilitan
#                           que el rival tome la esquina adyacente.
#     - Zona D (centro):  El resto del tablero.
#   El valor de cada zona NO es fijo: escala dinámicamente según cuántas celdas
#   hay ya ocupadas en el tablero (game_phase, de 0.0 a 1.0).
#   Al inicio, el centro tiene más peso (control del territorio).
#   Al final, esquinas y bordes dominan (estabilidad es lo que importa).
# ===========================================================================
class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "DensidadZonal"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Si el juego ha terminado usamos la diferencia real de fichas, amplificada
        # para que el árbol siempre prefiera ganar antes que cualquier otra opción.
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        # Identificar nuestro color y el del rival.
        # player_max puede ser player1 o player2 según quién sea MAX en este nodo.
        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        # Fase del juego: proporción de celdas ocupadas respecto al total (0.0-1.0).
        # Cuanto más lleno esté el tablero, más valiosas son las posiciones estables.
        game_phase = len(board) / (h * w)

        # Pesos de cada zona, escalados con la fase del juego:
        #   corner_weight:    80 (inicio) → 120 (final)
        #   border_weight:    10 (inicio) →  20 (final)
        #   subborder_weight: -5 (inicio) → -15 (final)  [peligrosas, penalizadas]
        #   center_weight:     2 (inicio) →   1 (final)
        corner_weight    =  80 + int(40 * game_phase)
        border_weight    =  10 + int(10 * game_phase)
        subborder_weight =  -5 - int(10 * game_phase)
        center_weight    =   2 - int( 1 * game_phase)

        # Coordenadas de las 4 esquinas (sistema 1-indexado que usa el juego)
        corners = {(1, 1), (1, h), (w, 1), (w, h)}

        score = 0.0
        for (x, y), color in board.items():
            # Ignorar celdas bloqueadas (obstáculos del torneo marcados con 'O')
            if color == 'O':
                continue

            # Clasificar la celda en su zona concéntrica
            is_corner    = (x, y) in corners
            is_border    = (x == 1 or x == w or y == 1 or y == h) and not is_corner
            is_subborder = (
                (x == 2 or x == w - 1 or y == 2 or y == h - 1)
                and not is_corner
                and not is_border
            )
            # Las celdas que no son ninguna de las anteriores pertenecen al centro

            # Asignar el peso de la zona correspondiente
            if is_corner:
                cell_value = corner_weight
            elif is_border:
                cell_value = border_weight
            elif is_subborder:
                cell_value = subborder_weight
            else:
                cell_value = center_weight

            # Sumar al score si es nuestra ficha; restar si es del rival
            if color == me:
                score += cell_value
            elif color == rival:
                score -= cell_value

        return float(score)


# ===========================================================================
# HEURÍSTICA DE RESPALDO 1 — Solution2
# Nombre: ControlEsquinas
# Uso: respaldo en Solution2; se usará como heurística principal en Torneo 2
#      (sustituida por FrontierPenalty, pero sirve como segunda opción aquí).
# ===========================================================================
class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "ControlEsquinas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Las esquinas son posiciones absolutamente estables: una vez capturadas,
        # no pueden ser volteadas en ningún caso. Controlarlas es una ventaja
        # permanente. Esta heurística simplemente cuenta cuántas esquinas tiene
        # cada jugador y devuelve la diferencia.
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        corners = [(1, 1), (1, h), (w, 1), (w, h)]
        my_corners  = sum(1 for c in corners if board.get(c) == me)
        adv_corners = sum(1 for c in corners if board.get(c) == rival)

        return float(my_corners - adv_corners)


# ===========================================================================
# HEURÍSTICA DE RESPALDO 2 — Solution3
# Nombre: EsquinasYFichas
# Uso: tercera opción; combina control de esquinas con diferencia de fichas.
# ===========================================================================
class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "EsquinasYFichas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Heurística híbrida: premia fuertemente las esquinas (peso x50) y usa
        # la diferencia de fichas como criterio de desempate secundario.
        # La lógica es que el Minimax prefiera asegurar esquinas por encima de
        # cualquier otra consideración, y solo cuando no haya diferencia en
        # esquinas, prefiera capturar más fichas.
        if state.end_of_game:
            diff = state.scores[0] - state.scores[1]
            factor = 1000 if state.is_player_max(state.player1) else -1000
            return float(diff * factor)

        me = state.player_max.label
        rival = state.player1.label if me == state.player2.label else state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        corners = [(1, 1), (1, h), (w, 1), (w, h)]
        my_corners  = sum(1 for c in corners if board.get(c) == me)
        adv_corners = sum(1 for c in corners if board.get(c) == rival)

        my_coins  = sum(1 for c in board.values() if c == me)
        adv_coins = sum(1 for c in board.values() if c == rival)

        return float((my_corners - adv_corners) * 50 + (my_coins - adv_coins))
