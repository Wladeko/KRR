from abc import ABC, abstractmethod
from source.graph.transition_graph import TransitionGraph, StateNode, Edge
from source.parsers.logical_formula_parser import LogicalFormulaParser
from typing import List, Dict

class CustomParser(ABC):
    def __init__(self, transition_graph: TransitionGraph):
        self.transition_graph = transition_graph
        self.logical_formula_parser = LogicalFormulaParser()
        self.statements = []

    @abstractmethod
    def extract_fluents(self, statement: str) -> List[str]:
        pass

    @abstractmethod
    def parse(self, statement: str) -> None:
        pass

    def get_transition_graph(self) -> TransitionGraph:
        return self.transition_graph

    def evaluate_formula(self, formula: str, state: StateNode) -> bool:

        def replace_fluents_with_values(formula: str, state: StateNode) -> str:
            for fluent, value in state.fluents.items():
                formula = formula.replace(f"~{fluent}", str(not value))
                formula = formula.replace(fluent, str(value))
            return formula

        for logical_statement in self.logical_formula_parser.extract_logical_statements(formula):
            formula = replace_fluents_with_values(logical_statement, state)
            if eval(formula):
                return True
        return False

    def precondition_met(self, state: StateNode, precondition: str) -> bool:
        return self.evaluate_formula(precondition, state) or not precondition

class InitiallyParser(CustomParser):

    def get_initial_logic(self, statement: str) -> str:
        return statement.split("initially")[1].strip()

    def extract_fluents(self, statement: str) -> List[str]:
        formula = get_initial_logic(statement)
        return self.logical_formula_parser.extract_fluents(formula)
    
    def parse(self, statement: str) -> None:
        for state in self.transition_graph.generate_all_states():
            if self.evaluate_formula(get_initial_logic(statement), state):
                self.transition_graph.add_possible_initial_state(state)


class CausesParser(CustomParser):
    
    def extract_fluents(self, statement: str) -> List[str]:
        action, effect = map(str.strip, statement.split("causes"))
        
        effect_formula = effect.split(" if ")[0].strip()
        effect_fluents = self.logical_formula_parser.extract_fluents(effect_formula)
        
        precondition_formula = effect.split(" if ")[1] if " if " in effect else ""
        precondition_fluents = self.logical_formula_parser.extract_fluents(precondition_formula)
        
        return effect_fluents + precondition_fluents

    def parse(self, statement: str) -> None:
        action, effect = map(str.strip, statement.split("causes"))
        effect_formula = effect.split(" if ")[0].strip()
        precondition_formula = effect.split(" if ")[1] if " if " in effect else ""
        all_states = self.transition_graph.generate_all_states()
        
        for from_state in all_states:
            if self.precondition_met(from_state, precondition_formula):
                for statement in self.logical_formula_parser.extract_logical_statements(effect_formula):
                    to_state = from_state.copy()
                    for fluent, value in self.logical_formula_parser.extract_fluent_dict(statement).items():
                        to_state.fluents[fluent] = value
                    self.transition_graph.add_state(from_state)
                    self.transition_graph.add_state(to_state)
                    self.transition_graph.add_edge(from_state, action, to_state)

class ReleasesParser(CausesParser):

    def extract_fluents(self, statement: str) -> List[str]:
        statement = statement.replace("releases", "causes")
        super().extract_fluents(statement)

    def parse(self, statement: str) -> None:
        statement = statement.replace("releases", "causes")
        super().parse(statement)


class DurationParser(CustomParser):
    def extract_fluents(self, statement: str) -> List[str]:
        return []

    def parse(self, statement: str) -> None:
        action, duration = statement.split(" lasts ")
        for i, edge in enumerate(self.transition_graph.edges):
            if edge.action == action.strip() and edge.source != edge.target:
                edge.add_duration(int(duration))
                self.transition_graph.edges[i] = edge
