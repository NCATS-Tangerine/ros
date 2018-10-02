import argparse
import json
import requests
import os
import sys
import yaml
import time
import traceback
import ros.dag.conf as Conf
from ros.router import Router
from ros.util import Resource
from jsonpath_rw import jsonpath, parse
import networkx as nx
import uuid
from networkx.algorithms import lexicographical_topological_sort
from ros.graph import TranslatorGraphTools
from ros.kgraph import Neo4JKnowledgeGraph

class Workflow:
    ''' Execution logic. '''
    def __init__(self, spec, inputs={}):
        assert spec, "Could not find workflow."
        self.inputs = inputs
        self.stack = []
        self.spec = spec
        self.uuid = uuid.uuid4 ()
        self.graph = Neo4JKnowledgeGraph ()
        self.graph_tools = TranslatorGraphTools ()

        # resolve templates.
        templates = self.spec.get("templates", {})
        workflows = self.spec.get("workflow", {})
        
        for name, job in workflows.items ():
            extends = job.get ("code", None)
            if extends in templates:
                Resource.deepupdate (workflows[name], templates[extends], skip=[ "doc" ])

        """ Validate input and output parameters. """
        self.errors = []
        self.validate ()
       
        self.dag = nx.DiGraph ()
        operators = self.spec.get ("workflow", {}) 
        self.dependencies = {}
        jobs = {} 
        job_index = 0 
        print ("dependencies")
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

    def validate (self):
        """
        Enforce that input and output types of operators match their definitions.
        Validate the existence of implementations for each module/operator.
        """
        print ("validating")
        types_config = os.path.join(os.path.dirname(__file__), 'stdlib.yaml')
        with open (types_config, 'r') as stream:
            self.types = yaml.load (stream)['types']
            self.spec['types'] = self.types
            
        #print (json.dumps(self.types, indent=2))
        for job, node in self.spec.get("workflow", {}).items ():
            actuals = node.get("input", {})
            op = actuals.get("op","main")
            signature = node.get ("meta", {}).get (op, {}).get ("args", {})
            print (f"  {job}")
            for arg, arg_spec in signature.items ():
                arg_type = arg_spec.get ("type")
                arg_required = arg_spec.get ("required")
                print (f"    arg: type: {arg_type} required: {arg_required}")
                """ Specified type exists. """
                if not arg_type in self.types:
                    self.errors.append (f"Error: Unknown type {arg_type} referenced in job {job}.")
                else:
                    """ Required arguments are present in the job. """
                    if arg_required and not arg in actuals:
                        self.errors.append (f"Error: required argument {arg} not present in job {job}.")
        if len(self.errors) > 0:
            for error in self.errors:
                print (error)
            raise ValueError ("Errors encountered.")
        print ("Validation successful.")
        

    @staticmethod
    def get_workflow(workflow="mq2.ros", library_path=["."]):
        workflow_spec = None
        with open(workflow, "r") as stream:
            workflow_spec = yaml.load (stream.read ())
        return Workflow (Workflow.resolve_imports (workflow_spec, library_path))

    @staticmethod
    def resolve_imports (spec, library_path=["."]):
        print ("importing modules")
        imports = spec.get ("import", [])
        for i in imports:
            for path in library_path:
                file_name = os.path.join (path, f"{i}.ros")
                if os.path.exists (file_name):
                    with open (file_name, "r") as stream:
                        obj = yaml.load (stream.read ())
                        print (f"  module: {i} from {file_name}")
                        Resource.deepupdate (spec, obj, skip=[ "doc" ])
        return spec
    
    def set_result(self, job_name, value):
        self.spec.get("workflow",{}).get(job_name,{})["result"] = value 
    def get_result(self, job_name): #, value):
        return self.spec.get("workflow",{}).get(job_name,{}).get("result", None)
    def execute (self, router):
        ''' Execute this workflow. '''
        operators = router.workflow.get ("workflow", {})
        for operator in operators:
            print("")
            print (f"Executing operator: {operator}")
            op_node = operators[operator]
            op_code = op_node['code']
            args = op_node['args']
            result = router.route (self, operator, operator, op_node, op_code, args)
            self.persist_result (operator, result)
        return self.get_step(router, "return")["result"]
    def get_step (self, name):
        return self.spec.get("workflow",{}).get (name)
    def get_variable_name(self, name):
        result = None
        if isinstance(name, list):
            result = [ n.replace("$","") for n in name if n.startswith ("$") ]
        elif isinstance(name, str):
            result = name.replace("$","") if name.startswith ("$") else None
        return result
    def resolve_arg (self, name):
        return [ self.resolve_arg_inner (v) for v in name ] if isinstance(name, list) else self.resolve_arg_inner (name)
    def resolve_arg_inner (self, name):
        ''' Find the value of an argument passed to the workflow. '''
        value = name
        if name.startswith ("$"):
            var = name.replace ("$","")
            ''' Is this a job result? '''
            job_result = self.get_result (var)
            #print (f"job result {var}  ==============> {job_result}")
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
                #from_job = op_node.get("args",{}).get("inputs",{}).get("from", None) 
        except:
            traceback.print_exc ()
        elements = op_node.get("args",{}).get("elements",None) 
        if elements: 
            dependencies = elements
        for d in dependencies:
            print (f"  {op_node['code']}->{d}")
        return dependencies
    def generate_dependent_jobs(self, workflow_model, operator, dag):
        dependencies = []
        adjacency_list = { ident : deps for ident, deps in dag.adjacency() }
        op_node = self.spec["workflow"][operator]
        dependency_tasks = adjacency_list[operator].keys ()
        return [ d for d in dependency_tasks ]
    def json (self):
        return {
            "uuid" : self.uuid,
            "spec" : self.spec,
            "inputs" : self.inputs,
            "dependencies" : self.dependencies,
            "topsort" : self.topsort,
            "running" : {},
            "failed" : {},
            "done" : {}
        }

    """ Result management. """
    def form_key (self, job_name):
        ''' Form the key name. '''
        #print (f"---> {job_name}")
        return f"{self.uuid}.{job_name}.res"
    def set_result (self, job_name, value):
        ''' Set the result value. '''
        #print (f" writing output for job -------------> {job_name}")
        if not value:
            raise ValueError (f"Null value set for job_name: {job_name}")
        self.spec.get("workflow",{}).get(job_name,{})["result"] = value 
        self.graph_tools.to_knowledge_graph (
            in_graph = self.graph_tools.to_nx (value),
            out_graph = self.graph)
        
        key = self.form_key (job_name)
        if not os.path.exists ('cache'):
            os.mkdir ("cache")
        #print (f" ************> {key}")
        fname = os.path.join ("cache", key)
        with open(fname, "w") as stream:
            json.dump (value, stream, indent=2)
        #print (f"-------------------------> graph for {job_name} written.")
    def get_result (self, job_name):
        ''' Get the result graph. We pass the whole graph for every graph. '''
        result = None
        key = self.form_key (job_name)
        if not os.path.exists ('cache'):
            os.mkdir ("cache")
        #print (f" ************> {key}")
        fname = os.path.join ("cache", key)
        if os.path.exists (fname):
            with open(fname, "r") as stream:
                result = json.load (stream)
        #print (f"read>>>>> {json.dumps(result, indent=2)}")
        return result

if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description='Rosetta Workflow')
    arg_parser.add_argument('-w', '--workflow', help='Workflow to run', default="wf.yaml")
    arg_parser.add_argument('-a', '--args', help='An argument', action="append")
    args = arg_parser.parse_args ()

    #Env.log (f"Running workflow {args.workflow}")

    parser = Parser ()
    workflow = Workflow (
        spec = parser.parse (args.workflow),
        inputs = parser.parse_args (args.args))

    router = Router (workflow=workflow.spec)
    result = workflow.execute (router)
    print (f"result> {json.dumps(result,indent=2)}")
    
    # python parser.py -w mq2.yaml -a drug_name=imatinib
