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

# scaffold
def read_json (f):
    obj = Resource.get_resource_obj(f, format="json")
    print (f"{obj}")
    return obj

class Env:
    ''' Process utilities. '''
    @staticmethod
    def exit (message, status=0):
        print (f"Exiting. {message}")
        sys.exit (status)
        
    @staticmethod
    def error (message):
        Env.exit (f"Error: {message}", 1)

    @staticmethod
    def log (message):
        print (message)

class Parser:
    ''' Parsing logic. '''
    def parse (self, f):
        result = None
        with open(f,'r') as stream:
            result = yaml.load (stream.read ())
        return result #return Resource.get_resource_obj (f)
    def parse_args (self, args):
        result = {}
        for a in args:
            if '=' in a:
                k, v = a.split ('=')
                result[k] = v
                Env.log (f"Adding workflow arg: {k} = {v}")
            else:
                Env.error (f"Arg must be in format <name>=<value>")
        return result

class Workflow:
    ''' Execution logic. '''
    def __init__(self, spec, inputs={}):
        assert spec, "Could not find workflow."
        self.inputs = inputs
        self.stack = []
        self.spec = spec
        self.uuid = uuid.uuid4 ()
                        
        # resolve templates.
        templates = self.spec.get("templates", {})
        workflows = self.spec.get("workflow", {})
        
        for name, job in workflows.items ():
            extends = job.get ("extends", None)
            if extends:
                Resource.deepupdate (workflows[name], templates[extends], skip=[ "doc" ])
                #Resource.deepupdate (templates[extends], workflows[name], skip=[ "doc" ])
                #print (f"{name}=>{json.dumps(workflows[name], indent=2)}")
                
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

    @staticmethod
    def get_workflow(workflow="mq2.ros", library_path=["."]):
        workflow_spec = None
        with open(workflow, "r") as stream:
            workflow_spec = yaml.load (stream.read ())
        return Workflow (Workflow.resolve_imports (workflow_spec, library_path))

    @staticmethod
    def resolve_imports (spec, library_path=["."]):
        imports = spec.get ("import", [])
        for i in imports:
            for path in library_path:
                file_name = os.path.join (path, f"{i}.ros")
                if os.path.exists (file_name):
                    with open (file_name, "r") as stream:
                        obj = yaml.load (stream.read ())
                        print (f"importing module: {i} from {file_name}")
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
            result = router.route (self, operator, op_node, op_code, args)
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
#        pass
#    def resolve_arg (self, name):
        ''' Find the value of an argument passed to the workflow. '''
        value = name
        if name.startswith ("$"):
            var = name.replace ("$","")
            ''' Is this a job result? '''
            job_result = self.get_result (var)
            print (f"job result {var}  ==============> {job_result}")
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
        print (f" testing {arg_val} as dependency.")
        name = self.get_variable_name (arg_val)
        print (f"    name => {name}")
        if name and self.get_step (name):
            print (f"      adding dep: {name}")
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
        return dependencies
    def get_dependent_job_names0(self, op_node): 
        dependencies = []
        try:
            arg_list = op_node.get("args",{})
            for arg_name, arg_val in arg_list.items ():
                if isinstance(arg_val, list):
                    for i in list:
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
                
class RedisBackedWorkflow(Workflow):
    def __init__(self, spec, inputs):
        super(RedisBackedWorkflow, self).__init__(spec, inputs)
        '''
        self.redis = redis.Redis(
            host='hostname',
            port=port)
        '''
        self.redis = Redis (url=Conf.celery_result_backend.replace ("0", "1"))
    def form_key (self, job_name):
        return f"{self.uuid}.{job_name}.result",
    def set_result (self, job_name, value):
        self.redis.set (
            name=self.form_key(job_name),
            value=value)
    def get_result (self, job_name):
        return self.redis (name=self.form_key(job_name))

                
class Neo4JBackedWorkflow(Workflow):
    def __init__(self, spec, inputs):
        super(Neo4JBackedWorkflow, self).__init__(spec, inputs)
        self.redis = Redis (url=Conf.celery_result_backend.replace ("0", "1"))
    def form_key (self, job_name):
        return f"{self.uuid}.{job_name}.result",
    def set_result (self, job_name, value):
        self.redis.set (
            name=self.form_key(job_name),
            value=value)
    def get_result (self, job_name):
        return self.redis (name=self.form_key(job_name))

if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(description='Rosetta Workflow')
    arg_parser.add_argument('-w', '--workflow', help='Workflow to run', default="wf.yaml")
    arg_parser.add_argument('-a', '--args', help='An argument', action="append")
    args = arg_parser.parse_args ()

    Env.log (f"Running workflow {args.workflow}")

    parser = Parser ()
    workflow = Workflow (
        spec = parser.parse (args.workflow),
        inputs = parser.parse_args (args.args))

    router = Router (workflow=workflow.spec)
    result = workflow.execute (router)
    print (f"result> {json.dumps(result,indent=2)}")
    
    # python parser.py -w mq2.yaml -a drug_name=imatinib
