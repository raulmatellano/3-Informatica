import sys
from game import Player
from strategy import MinimaxAlphaBetaStrategy
from search import heuristic2

def get_player(max_depth: int = 3) -> Player:
    """
    Función obligatoria para el torneo. Devuelve una instancia de Player.
    Autores: Raul Matellano, Jorge Palomino
    """
    
    # Creamos la estrategia con nuestra Heurística 2 y Poda Alfa-Beta
    strategy = MinimaxAlphaBetaStrategy(
        heuristic=heuristic2,
        max_depth_minimax=max_depth,
        max_sec_per_evaluation=5, # El límite típico del torneo
        verbose=0
    )
    
    player = Player(
        name="IA Matellano-Palomino (AB-H2)",
        strategy=strategy,
        delay=0
    )
    
    return player

if __name__ == "__main__":
    player = get_player()
    print("Jugador de torneo cargado con éxito:", player.name)
