"""
    Equipo docente de Autómatas y Lenguajes Curso 2025-26
    Última modificación: 18 de septiembre de 2025
"""

from collections import deque
from graphviz import Digraph

"""
    Podéis implementar cualquier función auxiliar que consideréis necesaria
"""


def _get_all_transitions(automaton):
    automaton_all_transitions = []
    for state_ini in automaton.transitions:
        for symbol in automaton.transitions[state_ini]:
            for end_state in automaton.transitions[state_ini][symbol]:
                automaton_all_transitions.append(
                    (state_ini, symbol, end_state))
    return automaton_all_transitions


def is_deterministic(automaton):
    """Check whether an automaton is deterministic."""
    checked = set()

    for start_state, symbol, end_state in _get_all_transitions(automaton):
        if symbol is None:
            return False
        if (start_state, symbol) in checked:
            return False
        checked.add((start_state, symbol))

    return True


class FiniteAutomaton:

    def __init__(self, initial_state, states, symbols, transitions, final_states):
        self.initial_state = initial_state
        self.states = list(states) if states is not None else []
        self.symbols = tuple(symbols) if symbols is not None else ()
        self.final_states = set(final_states) if final_states is not None else set()
        self.transitions = transitions if transitions is not None else {}        

    def add_transition(self, start_state, symbol, end_state):
        if start_state not in self.transitions:
            self.transitions[start_state] = {}
            
        if symbol not in self.transitions[start_state]:
            self.transitions[start_state][symbol] = set()
        
        self.transitions[start_state][symbol].add(end_state)

    def accepts(self, cadena):
        def clausura_lambda(estados):
            visitados = set(estados)       
            pendientes = list(estados)     
            
            while pendientes:
                estado = pendientes.pop()  
                
                if estado in self.transitions and None in self.transitions[estado]:
                    for destino in self.transitions[estado][None]:
                        if destino not in visitados:
                            visitados.add(destino)
                            pendientes.append(destino)
            return visitados

        
        estados_actuales = clausura_lambda({self.initial_state})

        for letra in cadena:
            siguientes_estados = set() 
            
            for estado in estados_actuales:
                if estado in self.transitions and letra in self.transitions[estado]:
                    siguientes_estados.update(self.transitions[estado][letra])
            
            estados_actuales = clausura_lambda(siguientes_estados)

        if estados_actuales & self.final_states:
            return True
        else:
            return False

    def to_deterministic(self):
        pass

    def to_minimized(self):
        pass

    def draw(self, path="./images/", filename="automata.png", view=False):
        dot = Digraph(comment="Automata", format="png")
        dot.attr(rankdir="LR")

        # Nodo invisible para punto inicial
        dot.node("", shape="none")

        # Almacenar estados
        for state in self.states:
            if state in self.final_states:
                dot.node(state, shape="doublecircle")
            else:
                dot.node(state, shape="circle")

        # Flecha al estado inicial
        dot.edge("", self.initial_state)

        # Almacenar transiciones
        for state_ini in self.transitions:
            for symbol in self.transitions[state_ini]:
                for state_fin in self.transitions[state_ini][symbol]:
                    dot.edge(state_ini, state_fin,
                             symbol if symbol is not None else "λ")

        dot.render(path+filename, view=view)
