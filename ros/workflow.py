import argparse
import importlib
import json
import logging
import requests
import os
import re
import sys
import yaml
import time
import traceback
from jsonpath_rw import jsonpath, parse
import networkx as nx
import uuid
from networkx.algorithms import lexicographical_topological_sort
from ros.router import Router
from ros.util import Resource
from ros.config import Config
from ros.graph import TranslatorGraphTools
from ros.kgraph import Neo4JKnowledgeGraph
from ros.util import JSONKit
from ros.cache import Cache

logger = logging.getLogger("ros")
logger.setLevel(logging.WARNING)

class Execution:
    def __init__(self):
        self.done = {}
        self.running = {}
        self.failed = {}
        
class Workflow:
    """
    Abstracts a directed acyclic graph (DAG) of interdependent jobs modeled in the Ros language.
    Provides a framework including:
    * A shared graph accessible via the Cypher query language.
    * Variables, templates, separate modules, a type system for input and output parameters.
    * An event model for passing context and parameters to graph operators.
    """
    def __init__(self, spec, inputs={}, config=None, libpath=["."], local_connection=True):
        assert spec, "Workflow specification is required."

        """ If we got a string rather than a dict, load the workflow. """
        self.libpath = libpath
        if isinstance(spec, str):
            if os.path.exists (spec):
                logger.info (f"Loading workflow: {spec}")
                with open (spec, "r") as stream:
                    spec = yaml.load (stream.read ())
            else:
                raise ValueError (f"File not found: {spec}")
            
        """ Set inputs, specification, generate a GUID, load configuration, and connect to the graph. """
        self.inputs = inputs
        self.spec = spec
        self.uuid = uuid.uuid4 ()
        self.config = Config (config)
        self.tools = TranslatorGraphTools ()
        if local_connection:
            self.cache = Cache (redis_host=self.config['REDIS_HOST'],
                                redis_port=self.config['REDIS_PORT'])
            db_host = self.config.get('NEO4J_HOST', "localhost")
            self.graph = Neo4JKnowledgeGraph (host=db_host)
        self.errors = []
        self.json = JSONKit ()

        """ Prepare to manage execution state. """
        self.execution = Execution ()

        """ Load plugins. """
        self.plugins = []
        plugin_config = self.config["plugins"]
        for plugin_def in plugin_config:
            name = plugin_def['name']
            driver = self.instantiate (plugin_def['driver'])
            self.plugins.append (driver)
            workflows = driver.workflows ()
            logger.debug (f"Connecting {name}: {driver}")
            logger.debug (f"  --workflows: {workflows}")

        """ Resolve imports. """
        self.resolve_imports ()

        """ Resolve template references in workflow jobs. """
        self.resolve_templates ()
        
        """ Validate input and output parameters. """
        self.validate ()

        """ Create the directed acyclic graph of the workflow. """
        self.create_dag ()

        """ Validate the workflow with respect to the schema. """
        self.enforce_specification ()
        
    def instantiate (self, class_name):
        """ Given a class name <module>.<classname>, load the module and instantiate the class. """
        module_name = ".".join (class_name.split(".")[:-1])
        class_name = class_name.split(".")[-1]
        module = importlib.import_module(module_name)
        the_class = getattr(module, class_name)
        return the_class ()
        
    def enforce_specification (self):
        """ Define the beginnings of a language specification. """

        """ Must include a version. For now, there is only one. """
        assert self.spec.get ('ros') == 0.1

        """ Validate workflow object. """
        workflow = self.spec.get ('workflow', {})
        assert len(workflow) > 0, "Workflow element exists but contains no steps."

        """ Validate information section. """
        info = self.spec.get ("info", {})
        assert info, "Missing 'info' section."
        version = info.get ("version")
        assert version, "Missing info version "
        assert re.match("^\d+?\.\d+?.\d+?$", version), "Version is not a float."

        title = info.get ("title")
        assert isinstance(title, str), "Title is not valid."

        description = info.get ("description")
        assert isinstance(description, str), "Description is not valid."

    def create_dag (self):
        """ Examine job dependencies and create a directed acyclic graph of jobs in the workflow. """
        logger.debug ("dag")        
        self.dag = nx.DiGraph ()
        operators = self.spec.get ("workflow", {})
        self.dependencies = {}
        jobs = {}
        job_index = 0
        for operator in operators:
            job_index = job_index + 1
            op_node = operators[operator]
            op_code = op_node['code']
            args = op_node['args']
            self.dag.add_node (operator, attr_dict={ "op_node" : op_node })
            dependencies = self.get_dependent_job_names (op_node)
            for d in dependencies:
                self.dag.add_edge (operator, d, attr_dict={})
        for job_name, op_node in self.spec.get("workflow",{}).items ():
            self.dependencies[job_name] = self.generate_dependent_jobs (self.spec, job_name, self.dag)
        self.topsort = [ t for t in reversed([
            t for t in lexicographical_topological_sort (self.dag) ])
        ]

    def resolve_imports (self):
        """ Import separately developed workflow modules into this workflow. """
        if 'import' in self.spec:
            imports = self.spec.get ("import", [])
            logger.debug ("import")
            for i in imports:
                imported = False
                for path in self.libpath:
                    file_name = os.path.join (path, f"{i}.ros")
                    if os.path.exists (file_name):
                        with open (file_name, "r") as stream:
                            obj = yaml.load (stream.read ())
                            logger.debug (f"  importing {i}@{file_name}")
                            Resource.deepupdate (self.spec, obj, skip=[ "doc" ])
                            imported = True
                if not imported:
                    raise ValueError (f"Unable to find resource: {i}")
            del self.spec["import"]

    def resolve_templates (self):
        """ Map template objects into the jobs referencing them within the workflow. """
        templates = self.spec.get("templates", {})
        workflow = self.spec.get("workflow", {})
        for name, job in workflow.items ():
            extends = job.get ("code", None)
            if extends in templates:
                Resource.deepupdate (workflow[name], templates[extends], skip=[ "doc" ])

    def validate (self):
        """
        Enforce that input and output types of operators match their definitions.
        Validate the existence of implementations for each module/operator.
        """
        logger.debug ("validate")
        types_config = os.path.join(os.path.dirname(__file__), 'stdlib.yaml')
        with open (types_config, 'r') as stream:
            self.types = yaml.load (stream)['types']
            self.spec['types'] = self.types
            
        for job, node in self.spec.get("workflow", {}).items ():
            actuals = node.get("input", {})
            op = actuals.get("op","main")
            signature = node.get ("meta", {}).get (op, {}).get ("args", {})
            logger.debug (f"  {job}")
            for arg, arg_spec in signature.items ():
                arg_type = arg_spec.get ("type")
                arg_required = arg_spec.get ("required")
                logger.debug (f"    arg: type: {arg_type} required: {arg_required}")
                """ Specified type exists. """
                if not arg_type in self.types:
                    self.errors.append (f"Error: Unknown type {arg_type} referenced in job {job}.")
                else:
                    """ Required arguments are present in the job. """
                    if arg_required and not arg in actuals:
                        self.errors.append (f"Error: required argument {arg} not present in job {job}.")
        if len(self.errors) > 0:
            for error in self.errors:
                logger.debug (error)
            raise ValueError ("Errors encountered.")
        logger.debug ("valid.")
        
    @staticmethod
    def get_workflow(workflow="mq2.ros", inputs={}, library_path=["."]):
        workflow_spec = None
        with open(workflow, "r") as stream:
            workflow_spec = yaml.load (stream.read ())
        return Workflow (workflow_spec, inputs=inputs, libpath=library_path)
    
    '''
    def set_result(self, job_name, value):
        self.spec.get("workflow",{}).get(job_name,{})["result"] = value
        
    def get_result(self, job_name): #, value):
        return self.spec.get("workflow",{}).get(job_name,{}).get("result", None)

    def execute (self, router):
        operators = self.spec.get ("workflow", {})
        for operator in operators:
            logger.debug (f"Executing operator: {operator}")
            op_node = operators[operator]
            op_code = op_node['code']
            args = op_node['args']
            result = router.route (self, operator, op_node, op_code, args)
            self.set_result (operator, result)
        return self.get_step("return")["result"]
    '''

    def get_step (self, name):
        return self.spec.get("workflow",{}).get (name)
    
    def get_variable_name(self, name):
        result = None
        if isinstance(name, list):
            result = [ n.replace("$","") for n in name if isinstance(n,str) and n.startswith ("$") ]
        elif isinstance(name, str):
            result = name.replace("$","") if isinstance(name,str) and name.startswith ("$") else None
        return result
    
    def resolve_arg (self, name):
        return [ self.resolve_arg_inner (v) for v in name ] if isinstance(name, list) else self.resolve_arg_inner (name)
    
    def resolve_arg_inner (self, name):
        ''' Find the value of an argument passed to the workflow. '''
        value = name
        if isinstance(name,str) and name.startswith ("$"):
            var = name.replace ("$","")
            ''' Is this a job result? '''
            job_result = self.get_result (var)
            if var in self.inputs:
                value = self.inputs[var]
                if "," in value:
                    value = value.split (",")
            elif job_result or isinstance(job_result, dict):
                value = job_result
            else:
                raise ValueError (f"Referenced undefined variable: {var}")
        return value
    
    def to_camel_case(self, snake_str):
        components = snake_str.split('_') 
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        return components[0] + ''.join(x.title() for x in components[1:])
    
    def add_step_dependency (self, arg_val, dependencies):
        name = self.get_variable_name (arg_val)
        if name and self.get_step (name):
            dependencies.append (name)
            
    def get_dependent_job_names(self, op_node): 
        dependencies = []
        try:
            arg_list = op_node.get("args",{})
            for arg_name, arg_val in arg_list.items ():
                if isinstance(arg_val, list):
                    for i in arg_val:
                        self.add_step_dependency (i, dependencies)
                else:
                    self.add_step_dependency (arg_val, dependencies)
            inputs = op_node.get("args",{}).get("inputs",{})
            if isinstance(inputs, dict):
                from_job = inputs.get("from", None) 
                if from_job:
                    dependencies.append (from_job)
        except:
            traceback.print_exc ()
        elements = op_node.get("args",{}).get("elements",None) 
        if elements: 
            dependencies = elements
        for d in dependencies:
            op = op_node['args'].get('op','')
            op = f".{op}" if len(op) > 0 else ''
            logger.debug (f"  dependency: {op_node['code']}{op}->{d}")
        return dependencies
    
    def generate_dependent_jobs(self, workflow_model, operator, dag):
        dependencies = []
        adjacency_list = { ident : deps for ident, deps in dag.adjacency() }
        op_node = self.spec["workflow"][operator]
        dependency_tasks = adjacency_list[operator].keys ()
        return [ d for d in dependency_tasks ]
    
    """ Result management. """
    def form_key (self, job_name):
        """ Form the key name. """
        return f"{self.uuid}.{job_name}.res"
    
    def set_result (self, job_name, value):
        """ Set the result value. """
        #assert value, f"Null value set for job_name: {job_name}"

        """ In memory. """
        self.spec.get("workflow",{}).get(job_name,{})["result"] = value

        """ Update the graph store. """
        if value:
            self.tools.to_knowledge_graph (
                in_graph = self.tools.to_nx (value),
                out_graph = self.graph)

        """ Cache. """
        key = self.form_key (job_name)
        self.cache.set (key, json.dumps(value, indent=2))

    def get_result (self, job_name):
        """ Get the result graph. We pass the whole graph for every graph. """
        result = None

        """ Cache. """
        key = self.form_key (job_name)
        val = self.cache.get (key)
        return json.loads (val) if val else None

    """ Manage variable and query resolution generically. """
    
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
        """ Implementation of a simple SQL like syntax combining jsonpath and workflow results. """
        """ Resolve arguments, including select statements, into values. """
        response = value
        if isinstance(value, str):
            syntax_valid = False
            tokens = value.split (" ")
            """ 1. select 2. <query> 3. from 4.<object> """
            query_field_count = 4 
            if len(tokens) == query_field_count: 
                select_keyword, pattern, from_keyword, source = tokens
                if select_keyword == 'select' and from_keyword == 'from':
                    pattern = pattern.strip ('"')
                    if source.startswith ("$"):
                        syntax_valid = True
                        resolved_source = event.context.resolve_arg (source)
                        logger.debug (f"resolved source {resolved_source} and pattern {pattern}.")
                        response = event.context.json.select (
                            query = pattern,
                            graph = resolved_source)
                        logger.debug (f"query-result: {response}")
            if not syntax_valid:
                logger.error (f"Incorrectly formatted statement: {value}. Supported syntax is 'select <pattern> from <variable>'.")
        return response
