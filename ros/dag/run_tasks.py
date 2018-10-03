import argparse
import json
import os
import requests
import sys
import time
import yaml
from celery import group
from celery.utils.graph import DependencyGraph
from celery.execute import send_task
from types import SimpleNamespace
from celery.result import AsyncResult
from jsonpath_rw import jsonpath, parse
from ros.router import Router
from ros.workflow import Workflow
from ros.ndex import NDEx
from ros.dag.tasks import exec_operator
from ros.dag.tasks import calc_dag

def get_workflow(workflow="mq2.ros", library_path=["."]):
    workflow_spec = None
    with open(workflow, "r") as stream:
        workflow_spec = yaml.load (stream.read ())
    return Workflow.resolve_imports (workflow_spec, library_path)

def call_api(workflow="mq2.ros", host="localhost", port=8080, args={}, library_path=["."]):
    workflow_spec = get_workflow (workflow, library_path)
    return requests.post (
        url = f"{host}:{port}/api/executeWorkflow",
        json = {
            "workflow" : workflow_spec,
            "args"     : args
        })

def run_job(j, wf_model, asynchronous=False):
    wf_model.topsort.remove (j)
    print (f"  run: {j}")
#    print (f"    sort> {wf_model.topsort}")
#    print (f"    done> {wf_model.done.keys()}")
    if asynchronous:
        wf_model.running[j] = exec_operator.delay (model2json(wf_model), j)
    else:
        wf_model.done[j] = exec_operator (model2json(wf_model), j)

def json2model(json):
    return SimpleNamespace (**json)
def model2json(model):
    return {
        "uuid" : model.uuid,
        "spec" : model.spec,
        "inputs" : model.inputs,
        "dependencies" : model.dependencies,
        "topsort" : model.topsort,
        "running" : {},
        "failed" : {},
        "done" : {}
    }

class CeleryDAGExecutor:
    def __init__(self, spec, inputs):
        self.spec = spec
        self.inputs = inputs
    def execute (self, async=False):
        ''' Dispatch a task to create the DAG for this workflow. '''
        model_dict = calc_dag(self.spec, inputs=self.inputs)
        #print (json.dumps (model_dict, indent=2))
        model = json2model (model_dict)
        total_jobs = len(model.topsort)
        ''' Iterate over topologically sorted job names. '''
        while len(model.topsort) > 0:
            for j in model.topsort:
                #print (f"test: {j}")
                if j in model.done:
                    break
                dependencies = model.dependencies[j]
                if len(dependencies) == 0:
                    ''' Jobs with no dependencies can be run w/o further delay. '''
                    run_job (j, model, asynchronous=async)
                else:
                    ''' Iff all of this jobs dependencies are complete, run it. '''
                    if all ([ d in model.done for d in dependencies ]):
                        run_job (j, model, asynchronous=async)
            completed = []
            ''' Manage our list of asynchronous jobs. '''
            for job_name, promise in model.running.items ():
                print (f"job {job_name} is ready:{promise.ready()} failed:{promise.failed()}")
                if promise.ready ():
                    completed.append (job_name)
                    model.done[job_name] = promise.get ()
                    sink = model.get("workflow",{}).get(c,{})
                    sink['result'] = model.done[c]
                elif promise.failed ():
                    completed.append (job_name)
                    model.failed[job_name] = promise.get ()
            for c in completed:
                print (f"removing {job_name} from running.")
                del model.running[c]
        return model.done['return']
                
def main ():
    arg_parser = argparse.ArgumentParser(description='Ros Workflow CLI',
                                         formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=57))
    arg_parser.add_argument('-a', '--api', help="Execute via API instead of locally.", action="store_true")
    arg_parser.add_argument('-w', '--workflow', help="Workflow to execute.", default="mq2.ros")
    arg_parser.add_argument('-s', '--server', help="Hostname of api server", default="localhost")
    arg_parser.add_argument('-p', '--port', help="Port of the server", default="80")
    arg_parser.add_argument('-i', '--arg', help="Add an argument expressed as key=val", action='append')
    arg_parser.add_argument('-o', '--out', help="Output the workflow result graph to a file. Use 'stdout' to print to terminal.")
    arg_parser.add_argument('-l', '--lib_path', help="A directory containing workflow modules.", action='append')
    arg_parser.add_argument('-n', '--ndex_id', help="Publish the graph to NDEx")
    arg_parser.add_argument('--validate', help="Validate inputs and outputs", action="store_true")
    args = arg_parser.parse_args ()
    print (args)
    
    """ Parse input arguments. """
    #wf_args = { k : v.replace('_', '') for k, v in [ arg.split("=") for arg in args.arg ] }
    wf_args = { k : v for k, v in [ arg.split("=") for arg in args.arg ] }
    response = None
    if args.api:
        """ Invoke a remote API endpoint. """
        response = call_api (workflow=args.workflow,
                             host=args.server,
                             port=args.port,
                             args=wf_args)
    else:
        """ Execute the workflow in process. """
        executor = CeleryDAGExecutor (
            spec=get_workflow (workflow=args.workflow, library_path=args.lib_path),
            inputs=wf_args)
        response = executor.execute ()
        if args.ndex_id:
            jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph")
            graph = [ match.value for match in jsonpath_query.find (response) ]
            print (f"{args.ndex_id} => {json.dumps(graph, indent=2)}")
            ndex = NDEx ()
            ndex.publish (args.ndex_id, graph)
    if args.out:
        if args.out == "stdout":
            print (f"{graph_text}")
        else:
            with open(args.out, "w") as stream:
                stream.write (json.dumps(response, indent=2))
            
if __name__ == '__main__':
    main (sys.argv)
