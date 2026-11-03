"""General utilities to work with automatas."""
import re
from automaton import FiniteAutomaton, _get_all_transitions, is_deterministic
from collections import deque, defaultdict


class FormatParseError(Exception):
    """Exception for parsing problems."""


class AutomataFormat():
    """Custom format to write and read automata."""

    re_comment = re.compile(r"\s*#\.*")  # : Final
    re_empty = re.compile(r"\s*")  # : Final
    re_automaton = re.compile(r"\s*Automaton:\s*")  # : Final
    re_state = re.compile(r"\s*(\w+)(?:\s*(final))?\s*")  # : Final
    re_transition = re.compile(r"\s*(\w+)\s*-(\S)?->\s*(\w+)\s*")  # : Final
    re_initial = re.compile(r"\s*ini\s(\w+)\s*-(\S)?->\s*(\w+)\s*")  # : Final
    re_symbols = re.compile(r"\s*Symbols:\s*(\S*)\s*")  # : Final

    @classmethod
    def read(cls, description):
        """Read the automaton string description in our custom format."""
        splitted_lines = description.splitlines()
        prelude_read = False

        states = []
        final_states = set()

        automata = FiniteAutomaton("", [], set(), {}, set())

        for line in splitted_lines:
            if cls.re_comment.fullmatch(line) or cls.re_empty.fullmatch(line):
                continue

            if prelude_read:
                match = cls.re_symbols.fullmatch(line)
                if match:
                    symbols_str = match.groups()[0]
                    symbols = tuple(symbols_str)
                    continue

                match = cls.re_state.fullmatch(line)
                if match:
                    state_name, final_text = match.groups()
                    states.append(state_name)
                    if bool(final_text):
                        final_states.add(state_name)
                    continue

                match = cls.re_initial.fullmatch(line)
                if match:
                    state_name = match.groups()[0]
                    initial_state = state_name
                    line = line.replace('ini ', '')

                match = cls.re_transition.fullmatch(line)
                if match:
                    state1_name, symbol, state2_name = match.groups()

                    automata.add_transition(
                        state1_name, symbol, state2_name)
                    continue

            elif cls.re_automaton.fullmatch(line):
                prelude_read = True
                continue

            raise FormatParseError(f"Invalid line: {line}")

        if initial_state is None:
            raise FormatParseError("No initial state defined")

        automata.initial_state = initial_state
        automata.symbols = symbols
        automata.states = states
        automata.final_states = final_states

        return automata


def deterministic_automata_isomorphism(automaton1, automaton2):
    """Check if two deterministic automata are the same but renamed."""
    if not is_deterministic(automaton1) or not is_deterministic(automaton2):
        raise ValueError("Automata are not deterministic")

    if set(automaton1.symbols) != set(automaton2.symbols):
        return None

    if len(automaton1.states) != len(automaton2.states):
        return None

    if len(_get_all_transitions(automaton1)) != len(_get_all_transitions(automaton2)):
        return None

    equiv_map: Dict[aut.State, aut.State] = {}
    pending = deque({(automaton1.initial_state, automaton2.initial_state)})
    transition_map1: DefaultDict[
        aut.State,
        Dict[Optional[str], aut.State],
    ] = defaultdict(dict)
    for t in _get_all_transitions(automaton1):
        transition_map1[t[0]][t[1]] = t[2]

    transition_map2: DefaultDict[
        aut.State,
        Dict[Optional[str], aut.State],
    ] = defaultdict(dict)
    for t in _get_all_transitions(automaton2):
        transition_map2[t[0]][t[1]] = t[2]

    while pending:
        state1, state2 = pending.pop()
        if (state1 in automaton1.final_states) != (state2 in automaton2.final_states):
            return None

        equiv_state = equiv_map.get(state1)
        if equiv_state:
            if equiv_state != state2:
                return None

        else:
            equiv_map[state1] = state2
            transitions1 = transition_map1[state1]
            transitions2 = transition_map2[state2]
            if len(transitions1) != len(transitions2):
                return None

            for symbol, final1 in transitions1.items():
                final2 = transitions2.get(symbol)
                if final2 is None:
                    return None

                pending.appendleft((final1, final2))

    return equiv_map
