"""Test evaluation of automatas."""
import unittest
from abc import ABC

from automaton import FiniteAutomaton
from utils import AutomataFormat, deterministic_automata_isomorphism


class TestTransform(ABC, unittest.TestCase):
    """Base class for string acceptance tests."""

    def _check_transform(self, automaton, expected):
        """Test that the transformed automaton is as the expected one."""

        automaton.draw(filename="automaton", view=False)

        transformed = automaton.to_deterministic()

        transformed.draw(filename="transformed", view=False)
        expected.draw(filename="expected", view=False)

        equiv_map = deterministic_automata_isomorphism(expected, transformed)

        self.assertTrue(equiv_map is not None)

    def test_case1(self):
        """Test Case 1."""
        automaton_str = """
        Automaton:
        Symbols: 01
        
        q0
        qf final
        
        ini q0 -0-> qf
        qf -1-> qf
        """

        automaton = AutomataFormat.read(automaton_str)

        expected_str = """
        Automaton:
        Symbols: 01
        
        q0
        qf final
        empty
        
        ini q0 -0-> qf
        q0 -1-> empty
        qf -0-> empty
        qf -1-> qf
        empty -0-> empty
        empty -1-> empty
        
        """

        expected = AutomataFormat.read(expected_str)

        self._check_transform(automaton, expected)
    
    def test_case2_ambiguedad_nfa(self):
        """Test Case 2: NFA con caminos alternativos."""
        automaton_str = """
        Automaton:
        Symbols: ab
        
        q0
        q1 final
        
        ini q0 -a-> q0
        q0 -a-> q1
        """
        automaton = AutomataFormat.read(automaton_str)
        
        expected_str = """
        Automaton:
        Symbols: ab
        
        d0
        d1 final
        empty
        
        ini d0 -a-> d1
        d0 -b-> empty
        d1 -a-> d1
        d1 -b-> empty
        empty -a-> empty
        empty -b-> empty
        """
        expected = AutomataFormat.read(expected_str)
        self._check_transform(automaton, expected)

    def test_case3_transiciones_lambda(self):
        """Test Case 3: NFA con transiciones lambda iniciales."""
        automaton_str = """
        Automaton:
        Symbols: 01
        
        q0
        q1 final
        
        ini q0 --> q1
        q0 -0-> q0
        """
        automaton = AutomataFormat.read(automaton_str)
        
        expected_str = """
        Automaton:
        Symbols: 01
        
        d0 final
        empty
        
        ini d0 -0-> d0
        d0 -1-> empty
        empty -0-> empty
        empty -1-> empty
        """
        expected = AutomataFormat.read(expected_str)
        self._check_transform(automaton, expected)


if __name__ == '__main__':
    unittest.main()