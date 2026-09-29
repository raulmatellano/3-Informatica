# ==========================================
# [MODIFICACIÓN ALUMNO]: HEURÍSTICAS PARA TORNEO
# ==========================================
# Por qué se ha hecho así:
# Este archivo contiene las clases de nuestras heurísticas para que la plataforma 
# del profesor (Moodle) las evalúe en el torneo. Hemos partido de un razonamiento progresivo:
# 1. Contar fichas (Miope pero rápido)
# 2. Controlar esquinas (Estratégico pero ignora las fichas)
# 3. Híbrido (Prioriza esquinas, pero desempata sumando puntos por cada ficha)
# Así demostramos que comprendemos que la clave en Reversi no es capturar piezas
# prematuramente, sino asegurar posiciones inmutables.
# ==========================================
from game import TwoPlayerGameState
from tournament import StudentHeuristic

class Solution1(StudentHeuristic):
    def get_name(self) -> str:
        return "DiferenciaFichas"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        # Heurística Básica (Fichas): Su objetivo es simplemente tener más fichas que el rival.
        # Es la heurística más intuitiva pero también la más miope, ya que en Reversi 
        # tener muchas fichas al principio suele dejarte sin movimientos legales después.
        
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
        # Heurística Intermedia (Esquinas): En Reversi, las esquinas (corners) son
        # casillas seguras porque una vez capturadas, no pueden ser volteadas.
        # Esta función evalúa quién tiene más esquinas dominadas.
        if state.end_of_game:
            score_diff = state.scores[0] - state.scores[1]
            # Multiplicamos el score final por un valor alto para priorizar victorias
            # absolutas si la rama lleva al final de la partida.
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
        # Heurística Avanzada Híbrida: Combina la estabilidad de capturar esquinas
        # con un peso menor a conseguir fichas. Las esquinas reciben un peso altísimo (x50).
        # Esto enseña al Minimax a preferir movimientos que aseguren esquinas, y solo 
        # cuando no haya esquinas en juego, preferirá capturar el mayor número de fichas.
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
