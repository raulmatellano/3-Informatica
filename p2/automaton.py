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
            return frozenset(visitados)
            
        simbolos_dfa = tuple(s for s in self.symbols if s is not None)
        estado_inicial_dfa = clausura_lambda({self.initial_state})
        
        estados_procesar = [estado_inicial_dfa]
        estados_dfa = {estado_inicial_dfa: "empty" if not estado_inicial_dfa else "d0"}
        
        transiciones_dfa = {}
        estados_finales_dfa = set()
        contador_estados = 1
        
        while estados_procesar:
            estado_actual = estados_procesar.pop(0)
            nombre_actual = estados_dfa[estado_actual]
            
            # Si contiene algun estado final, el nuevo estado es de aceptacion
            if any(e in self.final_states for e in estado_actual):
                estados_finales_dfa.add(nombre_actual)
                
            transiciones_dfa[nombre_actual] = {}
            
            for simbolo in simbolos_dfa:
                destinos = set()
                for e in estado_actual:
                    if e in self.transitions and simbolo in self.transitions[e]:
                        destinos.update(self.transitions[e][simbolo])
                
                nuevo_estado = clausura_lambda(destinos)
                
                if nuevo_estado not in estados_dfa:
                    if not nuevo_estado:
                        estados_dfa[nuevo_estado] = "empty"
                    else:
                        estados_dfa[nuevo_estado] = f"d{contador_estados}"
                        contador_estados += 1
                    estados_procesar.append(nuevo_estado)
                    
                nombre_destino = estados_dfa[nuevo_estado]
                transiciones_dfa[nombre_actual][simbolo] = {nombre_destino}
                
        afd = FiniteAutomaton(
            initial_state=estados_dfa[estado_inicial_dfa],
            states=list(estados_dfa.values()),
            symbols=simbolos_dfa,
            transitions=transiciones_dfa,
            final_states=estados_finales_dfa
        )
        return afd

    def to_minimized(self):
        # Eliminamos estados inaccesibles (BFS desde el inicio)
        alcanzables = {self.initial_state}
        pendientes = [self.initial_state]
        
        while pendientes:
            estado = pendientes.pop(0)
            if estado in self.transitions:
                for simbolo in self.transitions[estado]:
                    for destino in self.transitions[estado][simbolo]:
                        if destino not in alcanzables:
                            alcanzables.add(destino)
                            pendientes.append(destino)
                            
        estados_utiles = alcanzables
        finales_utiles = self.final_states.intersection(estados_utiles)
        no_finales = estados_utiles - finales_utiles
        
        # Particion inicial: finales y no finales
        particiones = []
        if finales_utiles:
            particiones.append(finales_utiles)
        if no_finales:
            particiones.append(no_finales)
            
        def obtener_indice_particion(estado, partes):
            for i, p in enumerate(partes):
                if estado in p:
                    return i
            return -1
            
        # Refinamiento de clases de equivalencia
        cambio = True
        while cambio:
            cambio = False
            nuevas_particiones = []
            
            for particion in particiones:
                grupos = {}
                for estado in particion:
                    clave = []
                    for simbolo in self.symbols:
                        if estado in self.transitions and simbolo in self.transitions[estado]:
                            destino = list(self.transitions[estado][simbolo])[0]
                            clave.append(obtener_indice_particion(destino, particiones))
                        else:
                            clave.append(-1)
                            
                    clave = tuple(clave)
                    if clave not in grupos:
                        grupos[clave] = set()
                    grupos[clave].add(estado)
                
                for grupo in grupos.values():
                    nuevas_particiones.append(grupo)
                    
            if len(nuevas_particiones) > len(particiones):
                cambio = True
                particiones = nuevas_particiones
                
        # Construimos el automata minimo resultante
        nombre_estado_min = {}
        for i, particion in enumerate(particiones):
            nombre = f"m{i}"
            for estado in particion:
                nombre_estado_min[estado] = nombre
                
        estado_inicial_min = nombre_estado_min[self.initial_state]
        estados_min = list(set(nombre_estado_min.values()))
        finales_min = {nombre_estado_min[e] for e in finales_utiles}
        
        transiciones_min = {}
        for estado_orig, estado_min in nombre_estado_min.items():
            if estado_min not in transiciones_min:
                transiciones_min[estado_min] = {}
            if estado_orig in self.transitions:
                for simbolo, destinos in self.transitions[estado_orig].items():
                    destino_orig = list(destinos)[0]
                    if destino_orig in nombre_estado_min:
                        destino_min = nombre_estado_min[destino_orig]
                        transiciones_min[estado_min][simbolo] = {destino_min}
                        
        afm = FiniteAutomaton(
            initial_state=estado_inicial_min,
            states=estados_min,
            symbols=self.symbols,
            transitions=transiciones_min,
            final_states=finales_min
        )
        return afm

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