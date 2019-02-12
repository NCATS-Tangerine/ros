# TranQL.py
#
#    TranQL is a query language for heterogenous federated knowledge sources.
#
#    The NCATS Data Translator program investigates the creation
#    of a data and computational engine to accelerate biomedical
#    insight.
#
#    It aims to do this through the design and large scale computational
#    interrelation of complex, heterogeneous biomedical knowledge.
#
#    Knowledge Sources
#
#       Knowledge sources provide semantically annotated graphs. In general,
#       nodes in the knowledge graph refer to entities defined in curated
#       ontologies.
#
#    Aggregators
#
#       A variety of processes exist for asking questions that span knowledge
#       sources, returning a knowledge graph referencing objects from disparate ontologies.
#
#    Reasoners
#
#       Reasoners apply analytics to knowledge graphs comprised of data from
#       multiple sources which, in addition to ontologies, will incorporate
#       graph analytics, machine learning, and statistical methods as needed.
#
#    TranQL borrows metaphors from both graph and relational query languages like
#    Cypher and SQL. We need both kinds of capabilities to address the range of
#    available data sets.

import json
import logging
import os
import sys
from ros.util import Context
from ros.util import JSONKit
from ros.util import Concept
from ros.util import LoggingUtil
from ros.tranqlast import TranQL_AST
from pyparsing import (Word, White, Literal, delimitedList, Optional,
    Group, alphas, alphanums, printables, Forward, oneOf, quotedString,
    ZeroOrMore, restOfLine, CaselessKeyword, ParserElement, LineEnd,
    pyparsing_common as ppc)

LoggingUtil.setup_logging (
    default_path=os.path.join(os.path.dirname(__file__), 'logging.yaml'))

logger = logging.getLogger (__name__)

class TranQLParser:
    """ Defines the language's grammar. """
    def __init__(self):
        """ A program is a list of statements.
        Statements can be 'set' or 'select' statements.
        """
        statement = Forward()
        SELECT, FROM, WHERE, SET, AS = map(CaselessKeyword, "select from where set as".split())
        
        ident          = Word( "$" + alphas, alphanums + "_$" ).setName("identifier")
        columnName     = delimitedList(ident, ".", combine=True).setName("column name")
        columnNameList = Group( delimitedList(columnName))
        tableName      = delimitedList(ident, ".", combine=True).setName("column name")
        tableNameList  = Group(delimitedList(tableName))
        
        SEMI,COLON,LPAR,RPAR,LBRACE,RBRACE,LBRACK,RBRACK,DOT,COMMA,EQ = map(Literal,";:(){}[].,=")
        arrow = Literal ("->")
        t_expr = Group(ident + LPAR + Word("$" + alphas, alphanums + "_$") + RPAR + ZeroOrMore(LineEnd())).setName("t_expr") | \
                 Word(alphas, alphanums + "_$") + ZeroOrMore(LineEnd())
        t_expr_chain = t_expr + ZeroOrMore(arrow + t_expr)
        
        whereExpression = Forward()
        and_, or_, in_ = map(CaselessKeyword, "and or in".split())
        
        binop = oneOf("= != < > >= <= eq ne lt le gt ge", caseless=True)
        realNum = ppc.real()
        intNum = ppc.signed_integer()
        
        columnRval = realNum | intNum | quotedString | columnName # need to add support for alg expressions
        whereCondition = Group(
            ( columnName + binop + (columnRval | Word(printables) ) ) |
            ( columnName + in_ + "(" + delimitedList( columnRval ) + ")" ) |
            ( columnName + in_ + "(" + statement + ")" ) |
            ( "(" + whereExpression + ")" )
        )
        whereExpression << whereCondition + ZeroOrMore( ( and_ | or_ ) + whereExpression )
        
        '''
        Assignment for handoff.
        '''
        setExpression = Forward ()
        setStatement = Group(
            ( ident ) |
            ( quotedString("json_path") + AS + ident("name") ) |
            ( "(" + setExpression + ")" )
        )
        setExpression << setStatement + ZeroOrMore( ( and_ | or_ ) + setExpression )
        
        optWhite = ZeroOrMore(LineEnd() | White())
        
        """ Define the statement grammar. """
        statement <<= (
            Group(
                Group(SELECT + t_expr_chain)("concepts") + optWhite + 
                Group(FROM + tableNameList) + optWhite + 
                Group(Optional(WHERE + whereExpression("where"), "")) + optWhite + 
                Group(Optional(SET + setExpression("set"), ""))("select")
            )
            |
            Group(
                SET + (columnName + EQ + ( quotedString | intNum | realNum ))
            )("set")
        )("statement")

        """ Make a program a series of statements. """
        self.program = statement + ZeroOrMore(statement)
        
        """ Make rest-of-line comments. """
        comment = "--" + restOfLine
        self.program.ignore (comment)

    def parse (self, line):
        """ Parse a program, returning an abstract syntax tree. """
        result = self.program.parseString (line)
        return TranQL_AST (result.asList ())
        
class TranQL:
    """
    Define the language interpreter. 
    It provides an interface to
      Execute the parser
      Generate an abstract syntax tree
      Execute statements in the abstract syntax tree.
    """
    def __init__(self):
        """ Initialize the interpreter. """
        self.parser = TranQLParser ()
        self.context = Context ()

    def execute (self, program):
        """ Execute a program - a list of statements. """
        ast = None
        if isinstance(program, str):
            ast = self.parser.parse (program)
        if not ast:
            raise ValueError (f"Unhandled type: {type(program)}")
        for statement in ast.statements:
            logger.info (f"{statement}")
            statement.execute (interpreter=self)
            
if __name__ == "__main__":
    tranql = TranQL ()
    tranql.execute ("""
        -- Workflow 5
        --   Modules 1-4: Chemical Exposures by Clinical Clusters
        --      For sub-clusters within the overall ICEES asthma cohort defined by
        --      differential population density, which chemicals are related to these clusters
        --      with a p_value less than some threshold?
        --   Modules 5-*: Knowledge Graph Phenotypic Associations 
        --      For chemicals produced by the first steps, what phenotypes are associated with exposure
        --      to these chemicals?
        
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/'

        SELECT disease->chemical_substance
          FROM $icees.population_density_cluster
         WHERE disease = $disease
           AND population_density < $population_density
           AND cohort = $cohort
           AND max_p_value = $max_p_value
           SET '$.nodes.[*]' AS exposures

        SELECT chemical_substance->gene->biological_process->phenotypic_feature
          FROM $gamma.quick
         WHERE chemical_substance = $exposures
           SET knowledge_graph """)

