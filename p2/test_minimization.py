"""Test evaluation of automatas."""
import unittest
from abc import ABC

from automaton import FiniteAutomaton
from utils import AutomataFormat, deterministic_automata_isomorphism


class TestMinimize(ABC, unittest.TestCase):
    """Base class for string acceptance tests."""

    def _check_minimize(self, automaton, simplified):
        """Test that the minimized automaton is the simplified one."""
        minimized = automaton.to_minimized()
        equiv_map = deterministic_automata_isomorphism(minimized, simplified)

        self.assertTrue(equiv_map is not None)

    def test_empty_language(self):
        """Test an automaton for the empty language."""
        automaton_str = """
        Automaton:
            Symbols: a

            Initial
            NotReached1
            NotReached2
            Empty

            ini Initial -a-> Empty
            NotReached1 -a-> NotReached2
            NotReached2 -a-> Empty
            Empty -a-> Empty
        """

        automaton = AutomataFormat.read(automaton_str)

        simplified_str = """
        Automaton:
            Symbols: a

            Initial

            ini Initial -a-> Initial
        """

        simplified = AutomataFormat.read(simplified_str)

        self._check_minimize(automaton, simplified)

    def test_empty_str_language(self):
        """Test an automaton for the empty language."""
        automaton_str = """
        Automaton:
            Symbols: a

            Initial final
            NotReached1
            NotReached2
            Empty

            ini Initial -a-> Empty
            NotReached1 -a-> NotReached2
            NotReached2 -a-> Empty
            Empty -a-> Empty
        """

        automaton = AutomataFormat.read(automaton_str)

        simplified_str = """
        Automaton:
            Symbols: a

            Initial final
            Empty 

            ini Initial -a-> Empty
            Empty -a-> Empty
        """

        simplified = AutomataFormat.read(simplified_str)

        self._check_minimize(automaton, simplified)

    def test_redundant_states(self):
        """Test an automaton for the empty language."""
        automaton_str = """
        Automaton:
            Symbols: ab

            Initial
            B1 final
            B2 final
            Empty

            ini Initial -a-> B1
            Initial -b-> Empty
            B1 -a-> B1
            B1 -b-> B2
            B2 -a-> B1
            B2 -b-> B1
            Empty -a-> Empty
            Empty -b-> Empty
        """

        automaton = AutomataFormat.read(automaton_str)

        simplified_str = """
        Automaton:
            Symbols: ab

            Initial
            B final
            Empty

            ini Initial -a-> B
            Initial -b-> Empty
            B -a-> B
            B -b-> B
            Empty -a-> Empty
            Empty -b-> Empty
        """

        simplified = AutomataFormat.read(simplified_str).to_deterministic()

        self._check_minimize(automaton, simplified)


if __name__ == '__main__':
    unittest.main()
