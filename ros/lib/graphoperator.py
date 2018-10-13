import collections
import copy
import json
import logging
import requests
import yaml
from ros.framework import Operator

logger = logging.getLogger("graphOperator")
logger.setLevel(logging.WARNING)

def update(d, u):
    """ Update values in d while preserving syblings of replaced keys at each level. """
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class Service:
    """ Describe a service to invoke. """
    def __init__(self, spec):
        self.url = spec['url']
        self.name = spec['name']
        self.response = None
        
class GraphOperator(Operator):    
    """ Model invoking graph operators in the network generically. """

    def __init__(self):
        pass
    
    def new_message (self, values):
        """ Create a new message populating omitted fields with defaults. """
        response = {
            "question_graph": {
                "nodes": [],
                "edges": []
            },
            "knowledge_graph": {
                "nodes": [],
                "edges": []
            },
            "knowledge_maps": []
        }
        update (response, values)
        return response
    
    def resolve(self, d, event, loop, index):
        result = d
        if isinstance(d, list):
            result = [ self.resolve(e, event, loop, index) for e in d ]
        elif isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, collections.Mapping):
                    result[k] = self.resolve(v, event, loop, index)
                elif isinstance(v, str):
                    if v.startswith('$'):
                        key = v[1:]
                        obj = loop[key][index] if key in loop and len(loop[key]) > index else None 
                        if not obj:
                            obj = event.context.resolve_arg (v)
                        result[k] = obj
                    if v.startswith('select '):
                        result[k] = self.resolve_query (v, event)
                elif isinstance(v, list):
                    result[k] = self.resolve (v, event, loop, index)
                else:
                    result[k] = v
        return result

    def resolve(self, d, event, loop, index):
        result = d
        if isinstance(d, list):
            result = [ self.resolve(e, event, loop, index) for e in d ]
        elif isinstance(d, dict):
            for k, v in d.items():
                result[k] = self.resolve(v, event, loop, index)
        elif isinstance(d, str):
            if d.startswith('$'):
                key = d[1:]
                obj = loop[key][index] if key in loop and len(loop[key]) > index else None 
                if not obj:
                    obj = event.context.resolve_arg (d)
                result = obj
            elif d.startswith('select '):
                result = self.resolve_query (d, event)
        return result

    def resolve_query (self, value, event):
        """ Resolve arguments, including select statements, into values. """
        response = value
        if isinstance(value, str):
            syntax_valid = False
            tokens = value.split (" ")
            if len(tokens) == 4:
                select_keyword, pattern, from_keyword, source = tokens
                if select_keyword == 'select' and from_keyword == 'from':
                    pattern = pattern.strip ('"')
                    if source.startswith ("$"):
                        syntax_valid = True
                        resolved_source = event.context.resolve_arg (source)
                        logger.debug (f"resolved source {resolved_source} and pattern {pattern}.")
                        response = event.context.json.select (
                            query = pattern,
                            obj = resolved_source)
                        logger.debug (f"query-result: {response}")
            if not syntax_valid:
                logger.error (f"Incorrectly formatted statement: {value}. Supported syntax is 'select <pattern> from <variable>'.")
        return response

    def invoke (self, event):
        """ Invoke a generic graph operator, or set of these. """
        
        """ Look for select statements and execute them to populate the outbound question. """
        """ This is limited to jsonpath_rw queries at the moment but is probably extensible to cypher. """
        """ Also need to dig deeper into the object hierarchy when executing statements. """
        responses = []
        loop = { k : self.resolve_query(v, event) for k, v in event.map.items () }

        """ Recursively process messages replacing variables, executing queries. """
        messages = []
        for index in range(0, len(loop)):
            archetype = self.new_message (event.message)
            messages.append (self.resolve (archetype, event, loop, index))

        """ Call them all. Package edges and nodes. """
        """ Will likely need more careful packaging to fully support chaining. """
        aggregate = [ self.invoke_service (event, message) for message in messages ]
        n = []
        e = []
        for a in aggregate:
            n = n + a[0]
            e = e + a[1]

        """ Return knowledge graph standard. """
        return event.context.graph_tools.kgs (nodes = n, edges = e)
            
    def short_text(self, text, max_len=85):
        """ Generate a shortened form of text. """
        return (text[:max_len] + '..') if len(text) > max_len else text

    def invoke_service(self, event, message):
        """ Invoke each service endpoint. """
        responses = []
        services = [ Service(s) for s in event.services ]
        for service in services:
            logger.debug (f"calling service: {service.url} => {json.dumps(message, indent=2)}")

            """ Invoke the service; stash the response. """
            service.response = requests.post (
                url = service.url,
                json = message,
                headers = { "accept" : "application/json" })

            if service.response.status_code == 200:
                logger.debug (f"Invoking service {service.url} succeeded.")
                responses.append (service.response.json ())
            else:
                logger.error (f"Service {service.url} failed with error {service.response.status_code} and error: {service.response.text}")

        """ kludgy, but works. """
        edges = []
        nodes = []
        for r in responses:
            for g in r['result_list']:
                print (json.dumps(g, indent=2))
                edges = edges + g['result_graph']['edge_list']
                nodes = nodes + g['result_graph']['node_list']
        #responses = event.context.graph_tools.kgs (nodes = nodes, edges = edges)
        '''
        """ fancy, but broken. """
        """ Select nodes and edges from all results and aggregate. """
        responses = event.context.graph_tools.kgs (
            nodes = event.context.json.select (
                query = "$.[*].result_list.[*].[*].result_graph.node_list.[*]",
                obj = responses),
            edges = event.context.json.select (
                query = "$.[*].result_list.[*].[*].result_graph.edge_list.[*]",
        obj = responses))
        '''
        t = self.short_text (json.dumps(responses, indent=2))
        print (f"responses: {t}")        
        #return responses

        return [ nodes, edges ]
