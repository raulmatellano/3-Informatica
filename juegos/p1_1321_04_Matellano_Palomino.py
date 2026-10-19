from game import TwoPlayerGameState
from tournament import StudentHeuristic


class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "Luna1"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            if state.is_player_max(state.player1):
                factor = 5000
            else:
                factor = -5000
            return float(dif * factor)
        me = state.player_max.label
        if me == state.player2.label:
            rival = state.player1.label
        else:
            rival = state.player2.label
        board = state.board
        h, w = state.game.height, state.game.width

        progreso = len(board) / (h * w)
        peso_esquina = 80 + int(40 * progreso)
        peso_borde = 10 + int(10 * progreso)
        peso_casiborde = -5 - int(10 * progreso)
        peso_centro = 1

        puntos = 0
        for (x, y), color in board.items():
            if color == "O":
                continue
            esquina = (
                (x == 1 and y == 1)
                or (x == 1 and y == h)
                or (x == w and y == 1)
                or (x == w and y == h)
            )
            borde = (x == 1 or x == w or y == 1 or y == h) and not esquina
            casiborde = (x == 2 or x == w - 1 or y == 2 or y == h - 1) and not borde

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


class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "JavisFather"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            if state.is_player_max(state.player1):
                factor = 5000
            else:
                factor = -5000
            return float(dif * factor)

        me = state.player_max.label
        if me == state.player2.label:
            rival = state.player1.label
        else:
            rival = state.player2.label

        board = state.board
        h, w = state.game.height, state.game.width
        vacias = 0
        for x in range(1, w + 1):
            for y in range(1, h + 1):
                if (x, y) not in board:
                    vacias += 1

        puntos_ultimo_turno = 0
        if vacias <= 14:
            if vacias % 2 != 0:
                puntos_ultimo_turno = 80  
            else:
                puntos_ultimo_turno = -80 

        puntos_esquinas = 0
        esquinas = [(1, 1), (1, h), (w, 1), (w, h)]
        for x, y in esquinas:
            ficha = board.get((x, y))
            if ficha == me:
                puntos_esquinas += 100
            elif ficha == rival:
                puntos_esquinas -= 100

        puntos_peligro = 0
        diagonal = [(2, 2), (2, h - 1), (w - 1, 2), (w - 1, h - 1)]
        lateral = [
            (1, 2),
            (2, 1),
            (1, h - 1),
            (2, h),
            (w - 1, 1),
            (w, 2),
            (w - 1, h),
            (w, h - 1),
        ]

        for x, y in diagonal:
            if x < w / 2:
                esq_x = 1
            else:
                esq_x = w            
            if y < h / 2:
                esq_y = 1
            else:
                esq_y = h 
            if board.get((esq_x, esq_y)) is None:
                ficha = board.get((x, y))
                if ficha == me:
                    puntos_peligro -= 40
                elif ficha == rival:
                    puntos_peligro += 40

        for x, y in lateral:
            if x <= 2:
                esq_x = 1
            else:
                esq_x = w

            if y <= 2:
                esq_y = 1
            else:
                esq_y = h
            if board.get((esq_x, esq_y)) is None:
                ficha = board.get((x, y))
                if ficha == me:
                    puntos_peligro -= 15
                elif ficha == rival:
                    puntos_peligro += 15

        puntos_bordes = 0
        for x in range(3, w - 1):
            ficha_arriba = board.get((x, 1))
            if ficha_arriba == me:
                puntos_bordes += 10
            elif ficha_arriba == rival:
                puntos_bordes -= 10

            ficha_abajo = board.get((x, h))
            if ficha_abajo == me:
                puntos_bordes += 10
            elif ficha_abajo == rival:
                puntos_bordes -= 10

        for y in range(3, h - 1):
            ficha_izq = board.get((1, y))
            if ficha_izq == me:
                puntos_bordes += 10
            elif ficha_izq == rival:
                puntos_bordes -= 10

            ficha_der = board.get((w, y))
            if ficha_der == me:
                puntos_bordes += 10
            elif ficha_der == rival:
                puntos_bordes -= 10
        mi_frontera = 0
        su_frontera = 0
        mis_fichas = 0
        sus_fichas = 0
        direcciones = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        for (x, y), ficha in board.items():
            if ficha == "O":
                continue

            if ficha == me:
                mis_fichas += 1
            elif ficha == rival:
                sus_fichas += 1

            es_frontera = False
            for dx, dy in direcciones:
                nx = x + dx
                ny = y + dy
                if 1 <= nx <= w and 1 <= ny <= h:
                    if (nx, ny) not in board:
                        es_frontera = True
                        break

            if es_frontera:
                if ficha == me:
                    mi_frontera += 1
                elif ficha == rival:
                    su_frontera += 1

        puntos_frontera = (su_frontera - mi_frontera) * 5

        puntos_minimizacion = 0
        if vacias > 14:
            puntos_minimizacion = (sus_fichas - mis_fichas) * 2
        puntos = (
            puntos_esquinas
            + puntos_peligro
            + puntos_bordes
            + puntos_frontera
            + puntos_ultimo_turno
            + puntos_minimizacion
        )

        return float(puntos)

class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "UltimaEsperanza"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            dif = state.scores[0] - state.scores[1]
            if state.is_player_max(state.player1):
                return float(dif * 10000)
            else:
                return float(dif * -10000)

        yo = state.player_max.label
        if yo == state.player2.label:
            rival = state.player1.label
        else:
            rival = state.player2.label

        board = state.board
        w = state.game.width
        h = state.game.height

        mis_fichas = 0
        sus_fichas = 0
        vacias = 0
        mi_frontera = 0
        su_frontera = 0
        
        puntos_esquinas = 0
        puntos_peligro = 0
        puntos_bordes = 0

        direcciones = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for x in range(1, w + 1):
            for y in range(1, h + 1):
                ficha = board.get((x, y))

                if ficha is None:
                    vacias += 1
                elif ficha == yo or ficha == rival:
                    if ficha == yo:
                        mis_fichas += 1
                    else:
                        sus_fichas += 1

                    es_frontera = False
                    for dx, dy in direcciones:
                        nx = x + dx
                        ny = y + dy
                        if 1 <= nx <= w and 1 <= ny <= h:
                            if board.get((nx, ny)) is None:
                                es_frontera = True
                                break
                    if es_frontera:
                        if ficha == yo: mi_frontera += 1
                        else: su_frontera += 1

        esquinas = [(1, 1), (1, h), (w, 1), (w, h)]
        for ex, ey in esquinas:
            ficha_esq = board.get((ex, ey))
            if ficha_esq == yo:
                puntos_esquinas += 1000
            elif ficha_esq == rival:
                puntos_esquinas -= 1000

        casillas_x = [
            (2, 2, 1, 1), (2, h - 1, 1, h),
            (w - 1, 2, w, 1), (w - 1, h - 1, w, h)
        ]
        for cx, cy, ex, ey in casillas_x:
            ficha_esq = board.get((ex, ey))
            ficha_c = board.get((cx, cy))

            if ficha_esq is None:
                if ficha_c == yo: puntos_peligro -= 300
                elif ficha_c == rival: puntos_peligro += 300
            elif ficha_esq == yo:
                if ficha_c == yo: puntos_peligro += 50
            elif ficha_esq == rival:
                if ficha_c == rival: puntos_peligro -= 50

        casillas_c = [
            (1, 2, 1, 1), (2, 1, 1, 1),
            (1, h - 1, 1, h), (2, h, 1, h),
            (w - 1, 1, w, 1), (w, 2, w, 1),
            (w - 1, h, w, h), (w, h - 1, w, h)
        ]
        for cx, cy, ex, ey in casillas_c:
            ficha_esq = board.get((ex, ey))
            ficha_c = board.get((cx, cy))

            if ficha_esq is None:
                if ficha_c == yo: puntos_peligro -= 100
                elif ficha_c == rival: puntos_peligro += 100
            elif ficha_esq == yo:
                if ficha_c == yo: puntos_peligro += 20
            elif ficha_esq == rival:
                if ficha_c == rival: puntos_peligro -= 20

        for x in range(3, w - 1):
            if board.get((x, 1)) == yo: puntos_bordes += 20
            elif board.get((x, 1)) == rival: puntos_bordes -= 20

            if board.get((x, h)) == yo: puntos_bordes += 20
            elif board.get((x, h)) == rival: puntos_bordes -= 20

        for y in range(3, h - 1):
            if board.get((1, y)) == yo: puntos_bordes += 20
            elif board.get((1, y)) == rival: puntos_bordes -= 20

            if board.get((w, y)) == yo: puntos_bordes += 20
            elif board.get((w, y)) == rival: puntos_bordes -= 20

        puntos_frontera = (su_frontera - mi_frontera) * 15

        multiplicador_fichas = (25 - vacias) / 4.0
        puntos_fichas = (mis_fichas - sus_fichas) * multiplicador_fichas

        puntuacion = (
            puntos_esquinas +
            puntos_peligro +
            puntos_bordes +
            puntos_frontera +
            puntos_fichas
        )

        return float(puntuacion)
