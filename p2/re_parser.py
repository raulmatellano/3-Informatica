"""
    Equipo docente de Autómatas y Lenguajes Curso 2025-26
    Última modificación: 18 de septiembre de 2025
"""

from automaton import FiniteAutomaton


def _re_to_rpn(re_string):
    """
    Convert re to reverse polish notation (RPN).

    Does not check that the input re is syntactically correct.

    Args:
        re_string: Regular expression in infix notation. Type: str

    Returns:
        Regular expression in reverse polish notation. Type: str

    """
    stack = []  # List of strings
    rpn_string = ""
    for x in re_string:
        if x == "+":
            while len(stack) > 0 and stack[-1] != "(":
                rpn_string += stack.pop()
            stack.append(x)
        elif x == ".":
            while len(stack) > 0 and stack[-1] == ".":
                rpn_string += stack.pop()
            stack.append(x)
        elif x == "(":
            stack.append(x)
        elif x == ")":
            while stack[-1] != "(":
                rpn_string += stack.pop()
            stack.pop()
        else:
            rpn_string += x

    while len(stack) > 0:
        rpn_string += stack.pop()

    return rpn_string


class REParser():
    """Class for processing regular expressions in Kleene's syntax."""

    def __init__(self) -> None:
        self.state_counter = 0

    def _create_automaton_empty(self):
        """
        Create an automaton that accepts the empty language.

        Returns:
            Automaton that accepts the empty language. Type: FiniteAutomaton

        """
        ini = f"q{self.state_counter}"
        self.state_counter += 1
        
        return FiniteAutomaton(
            initial_state=ini,      
            states=[ini],           
            symbols=(),            
            transitions={},     
            final_states=set()     
        )
    def _create_automaton_lambda(self):
        """
        Create an automaton that accepts the empty string.

        Returns:
            Automaton that accepts the empty string. Type: FiniteAutomaton

        """
    
        estado = f"q{self.state_counter}"
        self.state_counter += 1
        
        return FiniteAutomaton(
            initial_state=estado,     
            states=[estado],          
            symbols=(),              
            transitions={},  
            final_states={estado}      
        )  

    def _create_automaton_symbol(self, symbol):
        """
        Create an automaton that accepts one symbol.

        Args:
            symbol: Symbol that the automaton should accept. Type: str

        Returns:
            Automaton that accepts a symbol. Type: FiniteAutomaton

        """
        ini = f"q{self.state_counter}"
        self.state_counter += 1
        
        fin = f"q{self.state_counter}"
        self.state_counter += 1
        
        aut = FiniteAutomaton(
            initial_state=ini,
            states=[ini, fin],        
            symbols=(symbol,),        
            transitions={},            
            final_states={fin}         
        )
        
        aut.add_transition(ini, symbol, fin)
        
        return aut    
        

    def _create_automaton_star(self, automaton):
        """
        Create an automaton that accepts the Kleene star of another.

        Args:
            automaton: Automaton whose Kleene star must be computed. Type: FiniteAutomaton

        Returns:
            Automaton that accepts the Kleene star. Type: FiniteAutomaton

        """
        new_ini = f"q{self.state_counter}"
        self.state_counter += 1
        
        new_fin = f"q{self.state_counter}"
        self.state_counter += 1
        nuevos_estados = automaton.states + [new_ini, new_fin]
        
        nuevas_transiciones = {}
        for estado in automaton.transitions:
            nuevas_transiciones[estado] = {}
            for simbolo in automaton.transitions[estado]:
                nuevas_transiciones[estado][simbolo] = set(automaton.transitions[estado][simbolo])
                
        aut = FiniteAutomaton(
            initial_state=new_ini,
            states=nuevos_estados,
            symbols=automaton.symbols,
            transitions=nuevas_transiciones,
            final_states={new_fin}
        )
        
        
        aut.add_transition(new_ini, None, new_fin)
        
        aut.add_transition(new_ini, None, automaton.initial_state)
        
        for vieja_meta in automaton.final_states:
            aut.add_transition(vieja_meta, None, new_fin)
            aut.add_transition(vieja_meta, None, automaton.initial_state)
            
        return aut

    def _create_automaton_union(self, automaton1, automaton2):
        """
        Create an automaton that accepts the union of two automata.

        Args:
            automaton1: First automaton of the union. Type: FiniteAutomaton.
            automaton2: Second automaton of the union. Type: FiniteAutomaton.

        Returns:
            Automaton that accepts the union. Type: FiniteAutomaton.

        """
        new_ini = f"q{self.state_counter}"
        self.state_counter += 1
        
        new_fin = f"q{self.state_counter}"
        self.state_counter += 1
        
        nuevos_estados = automaton1.states + automaton2.states + [new_ini, new_fin]
        
        nuevos_simbolos = tuple(set(automaton1.symbols + automaton2.symbols))
        
        nuevas_transiciones = {}
        
        for estado in automaton1.transitions:
            nuevas_transiciones[estado] = {}
            for simbolo in automaton1.transitions[estado]:
                nuevas_transiciones[estado][simbolo] = set(automaton1.transitions[estado][simbolo])
                
        for estado in automaton2.transitions:
            if estado not in nuevas_transiciones:
                nuevas_transiciones[estado] = {}
            for simbolo in automaton2.transitions[estado]:
                nuevas_transiciones[estado][simbolo] = set(automaton2.transitions[estado][simbolo])
                
        aut = FiniteAutomaton(
            initial_state=new_ini,
            states=nuevos_estados,
            symbols=nuevos_simbolos,
            transitions=nuevas_transiciones,
            final_states={new_fin}
        )
        
        aut.add_transition(new_ini, None, automaton1.initial_state)
        aut.add_transition(new_ini, None, automaton2.initial_state)
        
        for vieja_meta in automaton1.final_states:
            aut.add_transition(vieja_meta, None, new_fin)
            
        for vieja_meta in automaton2.final_states:
            aut.add_transition(vieja_meta, None, new_fin)           
        return aut

    def _create_automaton_concat(self, automaton1, automaton2):
        """
        Create an automaton that accepts the concatenation of two automata.

        Args:
            automaton1: First automaton of the concatenation. Type: FiniteAutomaton.
            automaton2: Second automaton of the concatenation. Type: FiniteAutomaton.

        Returns:
            Automaton that accepts the concatenation. Type: FiniteAutomaton.

        """
        nuevos_estados = automaton1.states + automaton2.states
        nuevos_simbolos = tuple(set(automaton1.symbols + automaton2.symbols))
        nuevas_transiciones = {}
        
        for estado in automaton1.transitions:
            nuevas_transiciones[estado] = {}
            for simbolo in automaton1.transitions[estado]:
                nuevas_transiciones[estado][simbolo] = set(automaton1.transitions[estado][simbolo])
                
        for estado in automaton2.transitions:
            if estado not in nuevas_transiciones:
                nuevas_transiciones[estado] = {}
            for simbolo in automaton2.transitions[estado]:
                nuevas_transiciones[estado][simbolo] = set(automaton2.transitions[estado][simbolo])
                
        aut = FiniteAutomaton(
            initial_state=automaton1.initial_state,
            states=nuevos_estados,
            symbols=nuevos_simbolos,
            transitions=nuevas_transiciones,
            final_states=set(automaton2.final_states)
        )
        for vieja_meta in automaton1.final_states:
            aut.add_transition(vieja_meta, None, automaton2.initial_state)
            
        return aut
    
    def create_automaton(
        self,
        re_string,
    ):
        """
        Create an automaton from a regex.

        Args:
            re_string: String with the regular expression in Kleene notation. Type: str

        Returns:
            Automaton equivalent to the regex. Type: FiniteAutomaton

        """
        if not re_string:
            return self._create_automaton_lambda()

        rpn_string = _re_to_rpn(re_string)

        stack = []  # list of FiniteAutomatons

        self.state_counter = 0
        for x in rpn_string:
            if x == "*":
                aut = stack.pop()
                stack.append(self._create_automaton_star(aut))
            elif x == "+":
                aut2 = stack.pop()
                aut1 = stack.pop()
                stack.append(self._create_automaton_union(aut1, aut2))
            elif x == ".":
                aut2 = stack.pop()
                aut1 = stack.pop()
                stack.append(self._create_automaton_concat(aut1, aut2))
            elif x == "λ":
                stack.append(self._create_automaton_lambda())
            else:
                stack.append(self._create_automaton_symbol(x))

        return stack.pop()
