"""Strategies for two player games.

   Authors:
        Fabiano Baroni <fabiano.baroni@uam.es>,
        Alejandro Bellogin Kouki <alejandro.bellogin@uam.es>
        Alberto Suárez <alberto.suarez@uam.es>
"""

# Autores: Raul Matellano, Jorge Palomino
# Grupo de prácticas: (rellenar)  Pareja: (rellenar)
# Descripción: Implementación de Minimax con poda Alfa-Beta para Reversi.

from __future__ import annotations  # For Python 3.7

from abc import ABC, abstractmethod
import time
from typing import List

import numpy as np

from game import TwoPlayerGame, TwoPlayerGameState
from heuristic import Heuristic


class Strategy(ABC):
    """Abstract base class for player's strategy."""

    def __init__(self, verbose: int = 0) -> None:
        """Initialize common attributes for all derived classes."""
        self.verbose = verbose

    @abstractmethod
    def next_move(
        self,
        state: TwoPlayerGameState,
        gui: bool = False,
    ) -> TwoPlayerGameState:
        """Compute next move."""

    def generate_successors(
        self,
        state: TwoPlayerGameState,
    ) -> List[TwoPlayerGameState]:
        """Generate state successors."""
        assert isinstance(state.game, TwoPlayerGame)
        successors = state.game.generate_successors(state)
        assert successors  # Error if list is empty
        return successors


class RandomStrategy(Strategy):
    """Strategy in which moves are selected uniformly at random."""

    def next_move(
        self,
        state: TwoPlayerGameState,
        gui: bool = False,
    ) -> TwoPlayerGameState:
        """Compute next move."""
        successors = self.generate_successors(state)
        return np.random.choice(successors)


class ManualStrategy(Strategy):
    """Strategy in which the player inputs a move."""

    def next_move(
        self,
        state: TwoPlayerGameState,
        gui: bool = False,
    ) -> TwoPlayerGameState:
        """Compute next move"""
        successors = self.generate_successors(state)

        assert isinstance(state.game, TwoPlayerGame)
        if gui:
            index_successor = state.game.graphical_input(state, successors)
        else:
            index_successor = state.game.manual_input(successors)

        next_state = successors[index_successor]

        if self.verbose > 0:
            print('My move is: {:s}'.format(str(next_state.move_code)))

        return next_state


class MinimaxStrategy(Strategy):
    """Minimax strategy."""

    def __init__(
        self,
        heuristic: Heuristic,
        max_depth_minimax: int,
        max_sec_per_evaluation: float = 0,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose)
        self.heuristic = heuristic
        self.max_depth_minimax = max_depth_minimax
        self.max_sec_per_evaluation = max_sec_per_evaluation
        self.timed_out = False

    def next_move(
        self,
        state: TwoPlayerGameState,
        gui: bool = False,
    ) -> TwoPlayerGameState:
        """Compute the next state in the game."""

        minimax_value, minimax_successor = self._max_value(
            state,
            self.max_depth_minimax,
        )

        if self.verbose > 0:
            if self.verbose > 1:
                print('\nGame state before move:\n')
                print(state.board)
                print()
            print('Minimax value = {:.2g}'.format(minimax_value))

        return minimax_successor

    def _min_value(
        self,
        state: TwoPlayerGameState,
        depth: int,
    ) -> float:
        """Min step of the minimax algorithm."""

        if state.end_of_game or depth == 0:
            if self.timed_out:
                minimax_value = 0
            else:
                time0 = time.time()
                minimax_value = self.heuristic.evaluate(state)
                time1 = time.time()
                timediff = time1 - time0
                if (self.max_sec_per_evaluation > 0) and (timediff > self.max_sec_per_evaluation):
                    print("Heuristic {} timeout: {} > {}".format(self.heuristic.get_name(), timediff, self.max_sec_per_evaluation))
                    self.timed_out = True
            minimax_successor = None
        else:
            minimax_value = np.inf

            for successor in self.generate_successors(state):
                if self.verbose > 1:
                    print('{}: {}'.format(state.board, minimax_value))

                successor_minimax_value, _ = self._max_value(
                    successor,
                    depth - 1,
                )

                if (successor_minimax_value < minimax_value):
                    minimax_value = successor_minimax_value
                    minimax_successor = successor

        if self.verbose > 1:
            print('{}: {}'.format(state.board, minimax_value))

        return minimax_value, minimax_successor

    def _max_value(
        self,
        state: TwoPlayerGameState,
        depth: int,
    ) -> float:
        """Max step of the minimax algorithm."""

        if state.end_of_game or depth == 0:
            if self.timed_out:
                minimax_value = 0
            else:
                time0 = time.time()
                minimax_value = self.heuristic.evaluate(state)
                time1 = time.time()
                timediff = time1 - time0
                if (self.max_sec_per_evaluation > 0) and (timediff > self.max_sec_per_evaluation):
                    print("Heuristic {} timeout: {} > {}".format(self.heuristic.get_name(), timediff, self.max_sec_per_evaluation))
                    self.timed_out = True
            minimax_successor = None
        else:
            minimax_value = -np.inf

            for successor in self.generate_successors(state):
                if self.verbose > 1:
                    print('{}: {}'.format(state.board, minimax_value))

                successor_minimax_value, _ = self._min_value(
                    successor,
                    depth - 1,
                )
                if (successor_minimax_value > minimax_value):
                    minimax_value = successor_minimax_value
                    minimax_successor = successor

        if self.verbose > 1:
            print('{}: {}'.format(state.board, minimax_value))

        return minimax_value, minimax_successor


class MinimaxAlphaBetaStrategy(Strategy):
    """Minimax alpha-beta strategy."""

    def __init__(
        self,
        heuristic: Heuristic,
        max_depth_minimax: int,
        max_sec_per_evaluation: float = 0,
        verbose: int = 0,
    ) -> None:
        super().__init__(verbose)
        self.heuristic = heuristic
        self.max_depth_minimax = max_depth_minimax
        self.max_sec_per_evaluation = max_sec_per_evaluation
        self.timed_out = False

    def next_move(
        self,
        state: TwoPlayerGameState,
        gui: bool = False,
    ) -> TwoPlayerGameState:
        """Compute the next state in the game."""
        # Autores: Raul Matellano, Jorge Palomino
        minimax_value, minimax_successor = self._max_value(
            state,
            self.max_depth_minimax,
            -np.inf,
            np.inf
        )

        if self.verbose > 0:
            if self.verbose > 1:
                print('\nGame state before move:\n')
                print(state.board)
                print()
            print('Minimax value = {:.2g}'.format(minimax_value))

        return minimax_successor

    def _min_value(self, state: TwoPlayerGameState, depth: int, alpha: float, beta: float) -> tuple[float, TwoPlayerGameState]:
        # MIN_VALUE: Intenta minimizar la utilidad (turno del rival).
        if state.end_of_game or depth == 0:
            if self.timed_out:
                minimax_value = 0
            else:
                time0 = time.time()
                minimax_value = self.heuristic.evaluate(state) # Evaluamos el estado si llegamos a una hoja
                time1 = time.time()
                if (self.max_sec_per_evaluation > 0) and ((time1 - time0) > self.max_sec_per_evaluation):
                    print(f"Heuristic {self.heuristic.get_name()} timeout")
                    self.timed_out = True
            return minimax_value, None
            
        minimax_value = np.inf # Iniciamos con infinito positivo porque buscamos minimizar
        minimax_successor = None

        for successor in self.generate_successors(state):
            if self.verbose > 1:
                print('{}: [{:.2g}, {:.2g}]'.format(state.board, alpha, beta))

            # Llamada recursiva a MAX para evaluar la respuesta a nuestra acción
            successor_minimax_value, _ = self._max_value(successor, depth - 1, alpha, beta)

            # Si encontramos un valor más pequeño, es mejor para el rival (y peor para nosotros)
            if successor_minimax_value < minimax_value:
                minimax_value = successor_minimax_value
                minimax_successor = successor

            # PODA ALFA: Si el valor mínimo encontrado aquí es menor o igual a 'alpha' (el mejor valor 
            # asegurado por MAX más arriba en el árbol), sabemos que MAX nunca elegirá esta rama. 
            # Por tanto, no perdemos tiempo evaluando más sucesores y cortamos la búsqueda aquí.
            if minimax_value <= alpha:
                return minimax_value, minimax_successor
                
            # Actualizamos beta (el mejor valor, es decir, el más bajo, asegurado por MIN hasta ahora)
            beta = min(beta, minimax_value)

        return minimax_value, minimax_successor

    def _max_value(self, state: TwoPlayerGameState, depth: int, alpha: float, beta: float) -> tuple[float, TwoPlayerGameState]:
        # MAX_VALUE: Intenta maximizar la utilidad (nuestro turno).
        if state.end_of_game or depth == 0:
            if self.timed_out:
                minimax_value = 0
            else:
                time0 = time.time()
                minimax_value = self.heuristic.evaluate(state) # Evaluamos la ventaja que tenemos en esta hoja
                time1 = time.time()
                if (self.max_sec_per_evaluation > 0) and ((time1 - time0) > self.max_sec_per_evaluation):
                    print(f"Heuristic {self.heuristic.get_name()} timeout")
                    self.timed_out = True
            return minimax_value, None
            
        minimax_value = -np.inf # Iniciamos con infinito negativo porque buscamos maximizar
        minimax_successor = None

        for successor in self.generate_successors(state):
            if self.verbose > 1:
                print('{}: [{:.2g}, {:.2g}]'.format(state.board, alpha, beta))

            # Llamada recursiva a MIN simulando el turno del rival
            successor_minimax_value, _ = self._min_value(successor, depth - 1, alpha, beta)

            # Si encontramos un valor más grande, es una mejor jugada para nosotros
            if successor_minimax_value > minimax_value:
                minimax_value = successor_minimax_value
                minimax_successor = successor

            # PODA BETA: Si el valor máximo encontrado es mayor o igual a 'beta' (el mejor valor, más bajo, 
            # asegurado por MIN más arriba), MIN nunca permitirá que el juego llegue hasta aquí, 
            # elegirá otra rama antes. Por tanto, podemos dejar de evaluar los sucesores.
            if minimax_value >= beta:
                return minimax_value, minimax_successor
                
            # Actualizamos alpha (el mejor valor, el más alto, asegurado por MAX hasta ahora)
            alpha = max(alpha, minimax_value)

        return minimax_value, minimax_successor
