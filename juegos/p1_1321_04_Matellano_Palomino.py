from game import TwoPlayerGameState
from tournament import StudentHeuristic

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "Sol1"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            if state.is_player_max(state.player1): 
                factor=5000
            else:
                factor=-5000
            return float(dif * factor)
        me = state.player_max.label
        if me == state.player2.label:
            rival = state.player1.label 
        else:
            rival = state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        progreso = len(board) / (h * w)
        peso_esquina= 80 + int(40 * progreso)
        peso_borde=10 + int(10 * progreso)
        peso_casiborde=-5 - int(10*progreso)  
        peso_centro=1

        puntos = 0
        for (x, y), color in board.items():
            if color == 'O':
                continue
            esquina= (x == 1 and y == 1) or (x == 1 and y == h) or (x == w and y == 1) or (x == w and y == h)          
            borde= (x == 1 or x == w or y == 1 or y == h) and not esquina
            casiborde = ((x == 2 or x == w - 1 or y == 2 or y == h - 1) and not borde)

            if esquina:
                valor_casilla = peso_esquina
            elif borde:
                valor_casilla = peso_borde
            elif casiborde:
                valor_casilla = peso_casiborde
            else:
                valor_casilla = peso_centro
            if color == me:
                puntos += valor_casilla
            elif color == rival:
                puntos -= valor_casilla

        return float(puntos)


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
