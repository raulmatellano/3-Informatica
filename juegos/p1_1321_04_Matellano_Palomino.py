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



class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "sol2"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            puntos1, puntos2 = state.scores
            if state.is_player_max(state.player1):
                return float((puntos1 - puntos2)*5000)
            else:
                return float((puntos2 - puntos1)*5000)

        p1 = state.player1.label
        p2 = state.player2.label
        yo = state.player_max.label
        if yo == p1:
            rival = p2
        else: 
            rival = p1
        
        h, w = state.game.height, state.game.width

        esquinas = [(1, 1), (1, h), (w, 1), (w, h)]
        misEsquinas = 0
        susEsquinas = 0
        
        for casilla in esquinas:
            ficha = state.board.get(casilla)
            if ficha == yo:
                misEsquinas += 1
            elif ficha == rival:
                susEsquinas += 1

        return float(misEsquinas - susEsquinas)


class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "sol3"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            puntos1, puntos2 = state.scores
            if state.is_player_max(state.player1):
                return float((puntos1 - puntos2)*5000)
            else:
                return float((puntos2 - puntos1)*5000)

        p1 = state.player1.label
        p2 = state.player2.label
        yo = state.player_max.label
        if yo == p1:
            rival = p2
        else: 
            rival = p1


        h, w = state.game.height, state.game.width
        esquinas = [(1, 1), (1, h), (w, 1), (w, h)]
        
        misEsquinas = 0
        susEsquinas = 0
        
        for casilla in esquinas:
            ficha = state.board.get(casilla)
            if ficha == yo:
                misEsquinas += 1
            elif ficha == rival:
                susEsquinas += 1
                    
        misFichas = 0
        susFichas = 0
        
        for ficha in state.board.values():
            if ficha == yo:
                misFichas += 1
            elif ficha == rival: 
                susFichas += 1
        


        return float((misEsquinas - susEsquinas) * 50 + (misFichas - susFichas))
