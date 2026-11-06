import sys
import numpy as np
from game import TwoPlayerGameState, TwoPlayerMatch
from reversi import Reversi
from tournament import Tournament
from p1_0000_00_Matellano_Palomino import Solution1, Solution2, Solution3

def create_reversi_match(player1, player2):
    game = Reversi(player1=player1, player2=player2, height=8, width=8)
    game_state = TwoPlayerGameState(game=game, board=None, initial_player=player1)
    return TwoPlayerMatch(game_state, max_seconds_per_move=10, gui=False)

tour = Tournament(max_depth=3, init_match=create_reversi_match, max_evaluation_time=5.0)

strats = {
    'S1_Grav': [Solution1],
    'S2_Dens': [Solution2],
    'S3_Posi': [Solution3],
}

print("Iniciando torneo de prueba entre las 3 heurísticas del Torneo 1...")
n = 2
scores, totals, names = tour.run(
    student_strategies=strats,
    increasing_depth=False,
    n_pairs=n,
    allow_selfmatch=False,
)

print('\ttotal:', end='')
for name1 in names:
    print('\t%s' % (name1), end='')
print()
for name1 in names:
    print('%s\t%d:' % (name1, totals[name1]), end='')
    for name2 in names:
        if name1 == name2 or name2 not in scores[name1]:
            print('\t---', end='')
        else:
            print('\t%d' % (scores[name1][name2]), end='')
    print()
