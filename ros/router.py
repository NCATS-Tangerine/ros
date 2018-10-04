import argparse
import copy
import json
import logging
import namedtupled
import os
import requests
import sys
import yaml
import time
import traceback
from jsonpath_rw import jsonpath, parse
from ros.config import Config
from ros.operator import Event
from ros.operator import Operator
from ros.lib.biothings import Biothings
from ros.lib.xray import XRay
from ros.lib.ndex import NDEx
from ros.lib.gamma import Gamma

logger = logging.getLogger("router")
logger.setLevel(logging.WARNING)

class Router:
    req = 0

    """ Route operator invocations through a common interface. """
    """ TODO: Plugin framework to allow a profile of domain specific modules to be imported (e.g. Translator, M2M, etc) """
    def __init__(self, workflow):
        self.r = {
            'biothings' : self.biothings,
            'gamma'     : self.gamma,
            'xray'      : self.xray,
            'ndex'      : self.ndex,
            'union'     : self.union,
            'get'       : self.http_get
        }
        self.workflow = workflow
        self.prototyping_count = 0
        self.create_template_adapters ()
        
    def create_template_adapters (self):
        """ Plug in template instances that define new operators. """
        for name, template in self.workflow.spec.get("templates", {}).items ():
            op = template.get ("code", None)
            method = self.r.get (op, None)
            if method:
                def invoke_template (context, job_name, node, op, args):
                    node['args'].update (template['args'])
                    return method (context, job_name, node, op, args)
                self.r[name] = invoke_template
        
    def short_text(self, text, max_len=85):
        """ Generate a shortened form of text. """
        return (text[:max_len] + '..') if len(text) > max_len else text

    def route (self, context, job_name, op_node, op, args):
        """ Route an operator invocation to the correct module. """
        result = None
        if op in self.r:
            """ Create a copy of the operator node from the workflow. """
            node_copy = copy.deepcopy (op_node)

            """ Resolve arguments to values. """
            node_copy['args'] = { k : context.resolve_arg (v) for k,v in args.items() }

            """ Pass all operators context and the operation node. """
            arg_list = {
                "context"  : context,
                "job_name" : job_name,
                "node"     : node_copy,
                "op"       : args.get('op', None),
                "args"     : node_copy['args']
            }
            """ Call the operator. """
            result = self.r[op](**arg_list)
            text = self.short_text (str(result))
            logger.debug (f"  --({job_name})>> {text}")
        else:
            raise ValueError (f"Unknown operator: {op}")
        return result
    
    def union (self, context, job_name, node, op, args):
        """ Union two lists. """
        return [ context.get_step(e)["result"] for e in args.get("elements",[]) ]

    def http_get(self, context, job_name, node, op, args):
        """ Do an HTTP GET. """
        event = Event (context, node)
        url = event.pattern.format (**event.node['args'])
        return context.graph_tools.kgs (
            nodes=requests.get(
                url = url,
                headers = {
                    'accept': 'application/json'
                }).json ())
    
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
