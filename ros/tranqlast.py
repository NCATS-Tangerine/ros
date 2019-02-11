import copy
import json
import logging
from ros.util import Concept

logger = logging.getLogger (__name__)

class Statement:
    """ The interface contract for a statement. """
    def execute (self, interpreter):
        pass
    
class SetStatement(Statement):
    """ Model the set statement's semantics and variants. """
    def __init__(self, variable, value, jsonpath_query=None):
        self.variable = variable
        self.value = value
        self.jsonpath_query = jsonpath_query
    def execute (self, interpreter):
        interpreter.context.set (self.variable, self.value)
    def __repr__(self):
        return f"SET {self.variable}={self.value}"
    
class SelectStatement:
    """
    Model a select statement.
    This entails all capabilities from specifying a knowledge path, service to invoke, constraints, and handoff.
    """
    def __init__(self):
        """ Initialize a new select statement. """
        self.concept_order = []
        self.concepts = {}
        self.service = None
        self.where = []
        self.set_statements = []

    def __repr__(self):
        return f"SELECT {self.concepts} from:{self.service} where:{self.where} set:{self.set_statements}"
        
    def question (self, nodes, edges):
        """ Generate the frame of a question. """
        return {
            "machine_question": {
                "edges": edges,
                "nodes": nodes
            }
        }
    def edge (self, source, target, type_name=None):
        """ Generate a question edge. """
        e = {
            "source_id": source,
            "target_id": target
        }
        if type_name:
            e["type_name"] = type_name
        return e
    def node (self, identifier, type_name, value=None):
        """ Generate a question node. """
        logger.debug (f"value -> {value}")
        n = {
            "id": identifier,
            "type": type_name
        }
        if value:
            n ['curie'] = value 
        return n

    def val(self, value, field="id"):
        """ Get the value of an object. """
        result = value
        if isinstance(value, dict) and field in value:
            result = value[field]
        return result
    
    def execute (self, interpreter):
        """ Execute all statements in the abstract syntax tree. """
        questions = self.generate_questions ()
        for q in questions:
            print (f"  --question: {q}")
            
    def generate_questions (self):
        """ Given an archetype question graph and values, generate question
        instances for each value permutation. """
        for index, type_name in enumerate(self.concept_order):
            for value in self.concepts[type_name].nodes:
                if isinstance (value, list):
                    """ It's a list. Build the set and permute. """
                    self.concepts[name].nodes = [ self.node (
                        identifier = index,
                        type_name = type_name,
                        value = self.val(v)) for v in value ]
                elif isinstance (value, str):
                    self.concepts[type_name].nodes = [ self.node (
                        identifier = index,
                        type_name = type_name,
                        value = self.val(value)) ]
            else:
                self.concepts[type_name].nodes = [ self.node (
                    identifier = index,
                    type_name = type_name) ]

        edges = []
        questions = []
        for index, type_name in enumerate (self.concept_order):
            concept = self.concepts [type_name]
            logger.debug (f"concept: {concept}")
            previous = self.concept_order[index-1] if index > 0 else None
            if index == 0:
                for node in concept.nodes:
                    """ Model the first step. """
                    questions.append (self.question (
                        nodes = [ node ],
                        edges = []))
            else:
                new_questions = []
                for question in questions:
                    logger.debug (f"question: {question}")
                    for node in concept.nodes:
                        """ Permute each question. """
                        nodes = copy.deepcopy (question["machine_question"]['nodes'])
                        lastnode = nodes[-1]
                        nodes.append (node)
                        edges = copy.deepcopy (question["machine_question"]['edges'])
                        edges.append (self.edge (
                            source=lastnode['id'],
                            target=node['id']))
                        new_questions.append (self.question (
                            nodes = nodes,
                            edges = edges))
                questions = new_questions
        return questions
    
class TranQL_AST:
    """Represent the abstract syntax tree representing the logical structure of a parsed program."""
    def __init__(self, parse_tree):
        """ Create an abstract syntax tree from the parser token stream. """
        self.statements = []
        self.parse_tree = parse_tree
        for index, element in enumerate(self.parse_tree):
            if isinstance (element, list):
                statement = self.remove_whitespace (element, also=["->"])
                if element[0] == 'set':
                    if len(element) == 4:
                        self.statements.append (SetStatement (
                            variable = element[1],
                            value = element[3]))
                        
                    # ------- TODO
                    # ------- TODO
                    pass                
                elif isinstance(element[0], list):
                    statement = self.remove_whitespace (element[0], also=["->"])
                    if statement[0] == 'select':
                        self.parse_select (element)
                        
    def remove_whitespace (self, group, also=[]):
        """
        Delete spurious items in a statement.
        TODO: Look at enhancing the parser to provider cleaner input in the first place.
        """
        return [ x for x in group if not str(x).isspace () and not x in also ]
    
    def parse_select (self, statement):
        """ Parse a select statement. """
        select = SelectStatement ()
        for e in statement:
            if self.is_command (e):
                e = self.remove_whitespace (e, also=["->"])
                command = e[0]
                if command == 'select':
                    for token in e[1:]:
                        select.concept_order.append (token)
                        select.concepts[token] = Concept (token)
                if command == 'from':
                    select.service = e[1][0]
                elif command == 'where':
                    for condition in e[1:]:
                        if isinstance(condition, list) and len(condition) == 3:
                            var, op, val = condition
                            if var in select.concepts and op == "=":
                                select.concepts[var].nodes.append (val)
                            else:
                                select.where.append ([ var, op, val ])
                elif command == 'set':
                    if len(e[1]) == 3 or len(e[1]) == 1:
                        select.set_statements.append (e[1])
        self.statements.append (select)

    def is_command (self, e):
        """ Is this structured like a command? """
        return isinstance(e, list) and len(e) > 0
    
    def __repr__(self):
        return json.dumps(self.parse_tree, indent=2)
