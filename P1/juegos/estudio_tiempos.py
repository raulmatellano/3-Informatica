from __future__ import annotations

import timeit
from game import Player, TwoPlayerGameState
from heuristic import Heuristic
from reversi import Reversi
from strategy import MinimaxStrategy, MinimaxAlphaBetaStrategy
from tournament import StudentHeuristic

# Heurísticas del alumno
from p1_1321_04_Matellano_Palomino import Solution1, Solution2, Solution3


# Heurística determinista del profesor (Heuristic1 en demo_tournament.py)
class Heuristic1Profesor(StudentHeuristic):
    def get_name(self) -> str:
        return "Heuristic1"

    def evaluation_function(self, state: TwoPlayerGameState) -> float:
        return float(123 + 4)


def medir_tiempo(strategy_class, heuristic, depth, reps=5):
    player1 = Player("P1", None)
    player2 = Player("P2", None)
    game = Reversi(player1, player2, 8, 8)
    initial_state = TwoPlayerGameState(game, initial_player=player1).setup_match()

    strat = strategy_class(heuristic, depth, verbose=0)

    timer = timeit.default_timer
    start = timer()
    for _ in range(reps):
        strat.next_move(initial_state)
    total_duration = timer() - start

    return total_duration / reps


def main():
    sol1 = Solution1()
    sol2 = Solution2()
    sol3 = Solution3()

    heuristics = [
        ("Heuristic1 (profesor)", Heuristic("dummy", Heuristic1Profesor().evaluation_function)),
        (f"Solution1 ({sol1.get_name()})", Heuristic(sol1.get_name(), sol1.evaluation_function)),
        (f"Solution2 ({sol2.get_name()})", Heuristic(sol2.get_name(), sol2.evaluation_function)),
        (f"Solution3 ({sol3.get_name()})", Heuristic(sol3.get_name(), sol3.evaluation_function)),
    ]

    depths = [3, 4]
    filas = []

    for h_label, h_obj in heuristics:
        for d in depths:
            t_mm = medir_tiempo(MinimaxStrategy, h_obj, d, reps=5)
            t_ab = medir_tiempo(MinimaxAlphaBetaStrategy, h_obj, d, reps=5)
            speedup = t_mm / t_ab if t_ab > 0 else 1.0

            filas.append({
                "heuristica": h_label,
                "depth": d,
                "t_mm": t_mm,
                "t_ab": t_ab,
                "speedup": speedup,
            })

    # Tabla con las columnas imprescindibles del enunciado:
    # Heurística, Profundidad, Tiempos absolutos (Minimax y Alfa-Beta) y Medida independiente (Speedup)
    print("┌──────────────────────────────┬────────┬────────────────┬──────────────────┬───────────┐")
    print(f"│ {'Heurística':<28} │ {'Prof.':<6} │ {'Tiempo Minimax':<14} │ {'Tiempo Alfa-Beta':<16} │ {'Speedup':<9} │")
    print("├──────────────────────────────┼────────┼────────────────┼──────────────────┼───────────┤")

    for r in filas:
        print(
            f"│ {r['heuristica']:<28} │ d = {r['depth']:<2} │ "
            f"{r['t_mm']:.4f} s{'':<7} │ "
            f"{r['t_ab']:.4f} s{'':<9} │ "
            f"{r['speedup']:>5.2f}x{'':<3} │"
        )

    print("└──────────────────────────────┴────────┴────────────────┴──────────────────┴───────────┘")


if __name__ == "__main__":
    main()
