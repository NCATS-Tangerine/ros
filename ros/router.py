import argparse
import copy
import json
import namedtupled
import os
import requests
#import ros.dag.conf as Conf
import sys
import yaml
import time
import traceback
from jsonpath_rw import jsonpath, parse
from ros.config import Config
from ros.biothings import Biothings
from ros.xray import XRay
from ros.ndex import NDEx
from ros.gamma import Gamma
from ros.operator import Event
from ros.operator import Operator

class Router:
    req = 0

    ''' Route operator invocations through a common interface. '''
    ''' TODO: make this modular so that operators can be defined externally. Consider dynamic invocation. '''
    def __init__(self, workflow):
        self.r = {
            'biothings' : self.biothings,
            'gamma'     : self.gamma,
            'gamma_q'   : self.gamma_query,
            'xray'      : self.xray,
            'ndex'      : self.ndex,
            'union'     : self.union,
            'get'       : self.http_get
        }
        self.workflow = workflow
        self.prototyping_count = 0
        #return # still working on templates.
        for name, template in self.workflow.spec.get("templates", {}).items ():
            op = template.get ("code", None)
            method = self.r.get (op, None)
            if method:
                def invoke_template (context, job_name, node, op, args):
                    node['args'].update (template['args'])
                    return method (context, job_name, node, op, args)
                self.r[name] = invoke_template
        
    def short_text(self, text, max_len=85):
        return (text[:max_len] + '..') if len(text) > max_len else text

    def route (self, context, job_name, op_node, op, args):
        ''' Invoke an operator known to this router. '''
        result = None
        if op in self.r:
            ''' Pass all operators context and the operation node. '''
            node_copy = copy.deepcopy (op_node)

            ''' Resolve all arguments to values. '''
            node_copy['args'] = { k : context.resolve_arg (v) for k,v in args.items() }            
            arg_list = {
                "context"  : context,
                "job_name" : job_name,
                "node"     : node_copy,
                "op"       : args.get('op', None),
                "args"     : node_copy['args']
            }
            result = self.r[op](**arg_list)
            text = self.short_text (str(result))
            print (f"      result: {text}")
        else:
            raise ValueError (f"Unknown operator: {op}")
        return result
    def union (self, context, job_name, node, op, args):
        return [ context.get_step(e)["result"] for e in args.get("elements",[]) ]

    def http_get(self, context, job_name, node, op, args):
        event = Event (context, node)
        url = event.pattern.format (**event.node['args'])
        return context.graph_tools.kgs (
            nodes=requests.get(
                url = url,
                headers = {
                    'accept': 'application/json'
                }).json ())
    
    def naming_to_id (self, context, job_name, node, op, args):
        ''' An interface to bionames for resolving words to ids. '''
        input = args['input']
        type = args['type']
        return context.graph_tools.kgs (
            requests.get(
                url = f'https://bionames.renci.org/lookup/{input}/{type}/',
                headers = { 'accept': 'application/json' }).json ())
    
    def xray(self, context, job_name, node, op, args):
        return XRay ().invoke (
            event=Event (context=context,
                         node=node))

    def gamma(self, context, job_name, node, op, args):
        return Gamma ().invoke (
            event = Event (context=context,
                           node=node))
    
    def biothings(self, context, job_name, node, op, args):
        return Biothings ().invoke (
            Event (context=context,
                   node=node))

    def ndex (self, context, job_name, node):
        graph_obj = context.resolve_arg (graph)
        jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph")
        graph = [ match.value for match in jsonpath_query.find (graph_obj) ]
        print (f"{key} => {json.dumps(graph, indent=2)}")
        ndex = NDEx ()
        if op == "publish":
            ndex.publish (key, graph)

            
    def gamma_query (self, context, node, question, inputs):
        ''' An interface to the Gamma reasoner. '''
        # validate.

        ''' Build the query. '''
        select = inputs['select']
        jsonpath_query = parse (select)
        source = inputs['from']

        print (f"    *job(gamma): select: {select} from: {source}")

        ''' Get the data source. '''
        operators = self.workflow.spec.get ("workflow", {})
        if not source in operators:
            print (f"Error: Source {source} not found in workflow.")
        if not "result" in operators[source]:
            if source in context.done:
                operators[source]["result"] = context.done[source]
        if not "result" in operators[source]:
            print (f"Error: Source {source} has not computed a result.")
        data_source = operators[source]["result"]
        
        ''' Execute the query. '''
        values = [ match.value for match in jsonpath_query.find (data_source) ]

        if 'where' in inputs and 'return' in inputs:
            return_col = inputs['return']
            collector = []
            where = inputs['where']
            filter_col, filter_value = where.split ('=')
            print(f"where: {filter_col} {filter_value}")
            columns = None
            filter_col_index = -1
            return_col_index = -1
            if "." in select:
                select_parts = select.split (".")
                last = select_parts[-1:][0]
                print (f"....{last}")
                if "," in last:
                    columns = last.split (",")
                    print (f".....{columns}")
                    for c, column in enumerate(columns):
                        print (f"column: {c} {column}")
                        if column == filter_col:
                            filter_col_index = c
                        if column == return_col:
                            return_col_index = c
            print (f"values: {values}")
            if filter_col_index > -1 and return_col_index > -1:
                for i in range(0, len(values), len(columns)):
                    actual_col_value = values[i + filter_col_index]
                    print (f"Actual col val {actual_col_value} at {i} + {filter_col_index}")
                    if actual_col_value == filter_value:
                        collector.append (values[ i + return_col_index ])
            else:
                print (f"Error: Must specify valid where clause and return together.")        
            values = collector

        if len(values) == 0:
            raise ValueError ("no values selected")

        # Read a cached local version.
        self.req = self.req + 1
        cache = False #True
        if cache:
            cache_file = f"ranker_{self.req}.json"
            if os.path.exists (cache_file):
                answer = None
                with open(cache_file, "r") as stream:
                    answer = json.loads (stream.read ())
            elif os.path.exists ("ranker.json"):
                answer = None
                with open("ranker.json", "r") as stream:
                    answer = json.loads (stream.read ())
            return answer

        ''' Write the query. '''
        machine_question = {
            "machine_question": {
                "edges" : [],
                "nodes" : []
            }
        }

        ''' Get the list of transitions and add an input node with the selected values. '''
        ''' If machine questions don't handle lists, we'll need to work around this. '''
        ''' Set the type to the type of the first element of transitions. Document. '''
        ''' ckc, aug 21: Indeed, MQs do not handle first node lists.'''
        transitions = question["transitions"]
        node_id = 0

        ''' Build a machine question. '''
        machine_question["machine_question"]["nodes"].append ({
            "curie" : values[0],
            "id" : node_id,
            "type" : transitions[0]
        })
        for transition in transitions[1:]:
            node_id = node_id + 1
            machine_question["machine_question"]["nodes"].append ({
                "id" : node_id,
                "type" : transition
            })
            machine_question["machine_question"]["edges"].append ({
                "source_id" : node_id - 1,
                "target_id" : node_id
            })
        print (f"Gamma machine question: {json.dumps(machine_question,indent=2)}")

        ''' Send the query to Gamma and handle result. '''
        query_headers = {
            'accept' : 'application/json',
            'Content-Type' : 'application/json'
        }

        print (f"executing builder query: {self.workflow.config.robokop_builder_build_url}")
        builder_task_id = requests.post(
            url = self.workflow.config.robokop_builder_build_url,
            headers = query_headers,
            json = machine_question).json()
        print (f"{json.dumps(builder_task_id,indent=2)}")
        task_id = builder_task_id["task id"]
        
        break_loop = False
        print(f"Waiting for builder to update the Knowledge Graph.")
        while not break_loop:
          time.sleep(1)
          url = f"{self.workflow.config.robokop_builder_task_status_url}{task_id}"
          builder_status = requests.get(url).json ()
          print (f"{builder_status} {url}")
          if isinstance(builder_status, dict) and builder_status['status'] == 'SUCCESS':
              break_loop = True
        
        ranker_url = f"{self.workflow.config.robokop_ranker_now_url}"
        print (f"ranker url: {ranker_url}")
        answer = requests.post (
            url = ranker_url,
            headers = query_headers,
            json = machine_question).text #json()

        try:
            obj = json.loads (answer)
            answer = obj
            file_name= f"ranker-{self.req}.json"
            with open(file_name, "w") as stream:
                stream.write (json.dumps (obj, indent=2))
        except:
            print (f"unable to parse answer: {answer}")
            traceback.print_exc ()
        
        return answer
