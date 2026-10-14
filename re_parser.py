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
        
        # 2. Devolvemos el autómata
        return FiniteAutomaton(
            initial_state=estado,      # Casilla de salida
            states=[estado],           # Lista de casillas (solo hay una)
            symbols=(),                # No procesa letras reales
            transitions={},            # No hay puentes
            final_states={estado}      # ¡LA SALIDA ES LA META!
        )        # ---------------------------------------------------------------------

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
        1
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
        # ---------------------------------------------------------------------
        # TO DO: Implement this method...
        raise NotImplementedError("This method must be implemented.")
        # ---------------------------------------------------------------------

    def _create_automaton_union(self, automaton1, automaton2):
        """
        Create an automaton that accepts the union of two automata.

        Args:
            automaton1: First automaton of the union. Type: FiniteAutomaton.
            automaton2: Second automaton of the union. Type: FiniteAutomaton.

        Returns:
            Automaton that accepts the union. Type: FiniteAutomaton.

        """
        # ---------------------------------------------------------------------
        # TO DO: Implement this method...
        raise NotImplementedError("This method must be implemented.")
        # ---------------------------------------------------------------------

    def _create_automaton_concat(self, automaton1, automaton2):
        """
        Create an automaton that accepts the concatenation of two automata.

        Args:
            automaton1: First automaton of the concatenation. Type: FiniteAutomaton.
            automaton2: Second automaton of the concatenation. Type: FiniteAutomaton.

        Returns:
            Automaton that accepts the concatenation. Type: FiniteAutomaton.

        """
        # ---------------------------------------------------------------------
        # TO DO: Implement this method...
        raise NotImplementedError("This method must be implemented.")
        # ---------------------------------------------------------------------

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
