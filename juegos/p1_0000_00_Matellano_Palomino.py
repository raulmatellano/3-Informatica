from game import TwoPlayerGameState
from tournament import StudentHeuristic

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "DiferenciaFichas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Si el juego ha terminado, utilizamos el score real
        if state.end_of_game:
            score_diff = state.scores[0] - state.scores[1]
            return float(score_diff if state.is_player_max(state.player1) else -score_diff)
            
        me = state.player_max.label
        adversary = state.player1.label if me == state.player2.label else state.player2.label
        
        my_coins = sum(1 for c in state.board.values() if c == me)
        adv_coins = sum(1 for c in state.board.values() if c == adversary)
        return float(my_coins - adv_coins)

class Solution2(StudentHeuristic):
    def get_name(self) -> str:
        return "ControlEsquinas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            score_diff = state.scores[0] - state.scores[1]
            # Multiplicamos el score final por un valor alto para priorizar victorias
            return float(score_diff * 1000 if state.is_player_max(state.player1) else -score_diff * 1000)
            
        me = state.player_max.label
        adversary = state.player1.label if me == state.player2.label else state.player2.label
        
        corners = [(1, 1), (1, state.game.height), (state.game.width, 1), (state.game.width, state.game.height)]
        my_corners = sum(1 for c in corners if state.board.get(c) == me)
        adv_corners = sum(1 for c in corners if state.board.get(c) == adversary)
        
        # Las esquinas son la parte más valiosa de Reversi
        return float(my_corners - adv_corners)

class Solution3(StudentHeuristic):
    def get_name(self) -> str:
        return "EsquinasYFichas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        if state.end_of_game:
            score_diff = state.scores[0] - state.scores[1]
            return float(score_diff * 1000 if state.is_player_max(state.player1) else -score_diff * 1000)
            
        me = state.player_max.label
        adversary = state.player1.label if me == state.player2.label else state.player2.label
        
        corners = [(1, 1), (1, state.game.height), (state.game.width, 1), (state.game.width, state.game.height)]
        my_corners = sum(1 for c in corners if state.board.get(c) == me)
        adv_corners = sum(1 for c in corners if state.board.get(c) == adversary)
        
        my_coins = sum(1 for c in state.board.values() if c == me)
        adv_coins = sum(1 for c in state.board.values() if c == adversary)
        
        # Combinamos: gran peso a las esquinas, peso pequeño a las fichas
        return float((my_corners - adv_corners) * 50 + (my_coins - adv_coins))
