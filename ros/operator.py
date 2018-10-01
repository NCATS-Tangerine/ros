#import namedtupled
import json
from jsonpath_rw import jsonpath, parse

class Event:
    def __init__(self, context, node, op, graph=None):
        self.context = context
        self.node = node
        print (json.dumps (self.node, indent=2))
        self.op = op
        self.graph = graph
        #self.args = args

class Operator:

    ''' Abstraction of a graph operator. '''
    def __init__(self, name):
        self.name = name

    def invoke (self, event):
        ''' Invoke an operator. '''
        result = None
        operator = getattr (self, event.op)
        if operator:
            result = operator (event)
        else:
            raise ValueError (f"Unimplemented operator: {args.op}")
        return result

    @staticmethod
    def create_event (context, node, op, graph):
        ''' Create an event object. '''
        return  namedtupled.map ({
            "context" : context,
            "node" : node,
            "op" : op,
            "graph" : namedtupled.ignore (graph)
        })

    def query (self, graph, query):
        ''' Generic graph query method. '''
        jsonpath_query = parse (query)
        return [ match.value for match in jsonpath_query.find (graph) ]
    
    def get_nodes_by_type (self, graph, target_type, query="$.[*].result_list.[*].[*].result_graph.node_list.[*]"):
        ''' Query nodes by type. '''
        values = self.query (graph, query)
        '''
        jsonpath_query = parse (query)
        values = [ match.value for match in jsonpath_query.find (graph) ]
        '''
        return [ val for val in values if val['type'] == target_type ]
    
    def get_ids (self, nodes):
        ''' Get ids from graph nodes. '''
        return [ val['id'] for val in nodes ]
