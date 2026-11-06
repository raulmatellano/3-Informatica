from game import TwoPlayerGameState
from tournament import StudentHeuristic


class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "DensidadZonal"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            multiplicador = 1000 if state.is_player_max(state.player1) else -1000
            return float(dif * multiplicador)

        mi_color = state.player_max.label
        enemigo = state.player1.label if mi_color == state.player2.label else state.player2.label
        tablero = state.board
        alto, ancho = state.game.height, state.game.width

        ocupacion = len(tablero) / (alto * ancho)

        peso_esquina = 80 + int(40 * ocupacion)
        peso_borde = 10 + int(10 * ocupacion)
        peso_peligro = -5 - int(10 * ocupacion)
        peso_centro = 2 - int(1 * ocupacion)

        esquinas = {(1, 1), (1, alto), (ancho, 1), (ancho, alto)}

        puntaje_total = 0.0
        for (x, y), ficha in tablero.items():
            if ficha == 'O':
                continue

            es_esquina = (x, y) in esquinas
            es_borde = (x == 1 or x == ancho or y == 1 or y == alto) and not es_esquina
            es_zona_peligro = (
                (x == 2 or x == ancho - 1 or y == 2 or y == alto - 1)
                and not es_esquina
                and not es_borde
            )

            if es_esquina:
                valor_casilla = peso_esquina
            elif es_borde:
                valor_casilla = peso_borde
            elif es_zona_peligro:
                valor_casilla = peso_peligro
            else:
                valor_casilla = peso_centro

            if ficha == mi_color:
                puntaje_total += valor_casilla
            elif ficha == enemigo:
                puntaje_total -= valor_casilla

        return float(puntaje_total)


class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "ControlEsquinas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            multiplicador = 1000 if state.is_player_max(state.player1) else -1000
            return float(dif * multiplicador)

        mi_color = state.player_max.label
        enemigo = state.player1.label if mi_color == state.player2.label else state.player2.label
        tablero = state.board
        alto, ancho = state.game.height, state.game.width

        esquinas_juego = [(1, 1), (1, alto), (ancho, 1), (ancho, alto)]
        esquinas_nuestras = sum(1 for c in esquinas_juego if tablero.get(c) == mi_color)
        esquinas_suyas = sum(1 for c in esquinas_juego if tablero.get(c) == enemigo)

        return float(esquinas_nuestras - esquinas_suyas)


class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "EsquinasYFichas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            multiplicador = 1000 if state.is_player_max(state.player1) else -1000
            return float(dif * multiplicador)

        mi_color = state.player_max.label
        enemigo = state.player1.label if mi_color == state.player2.label else state.player2.label
        tablero = state.board
        alto, ancho = state.game.height, state.game.width

        esquinas_juego = [(1, 1), (1, alto), (ancho, 1), (ancho, alto)]
        esquinas_nuestras = sum(1 for c in esquinas_juego if tablero.get(c) == mi_color)
        esquinas_suyas = sum(1 for c in esquinas_juego if tablero.get(c) == enemigo)

        if state.is_player_max(state.player1):
            fichas_nuestras = state.scores[0]
            fichas_suyas = state.scores[1]
        else:
            fichas_nuestras = state.scores[1]
            fichas_suyas = state.scores[0]

        return float((esquinas_nuestras - esquinas_suyas) * 50 + (fichas_nuestras - fichas_suyas))
