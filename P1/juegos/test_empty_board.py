import demo_tournament
demo_tournament.create_match = demo_tournament.create_reversi_match
demo_tournament.strats = {'opt1': [demo_tournament.Heuristic1]}
# modify create_reversi_match
import sys
