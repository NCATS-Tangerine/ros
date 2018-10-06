import argparse
import contextlib
import json
import os
import requests
import logging
import logging.config
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
from ros.lib.ndex import NDEx
from ros.tasks import exec_operator
#from ros.tasks import exec_async
from ros.celery_tools import CeleryManager

import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger("runner")
logger.setLevel(logging.WARNING)

def execute_remote (workflow="mq2.ros", host="localhost", port=8080, args={}, library_path=["."]):
    """ Execute the workflow remotely via a web API. """
    workflow_spec = Workflow.get_workflow (workflow, library_path)
    return requests.post (
        url = f"{host}:{port}/api/executeWorkflow",
        json = {
            "workflow" : workflow_spec,
            "args"     : args
        })

def run_job(j, wf_model, asynchronous=False):
    wf_model.topsort.remove (j)
    logger.debug (f"  run: {j}")
    logger.debug (f"    sort> {wf_model.topsort}")
    logger.debug (f"    done> {wf_model.done.keys()}")
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

async def call_op (workflow, router, job_name, op_node):
    return workflow.set_result (
        job_name,
        router.route (workflow, job_name, op_node, op_node['code'], op_node['args']))
    
async def exec_async (workflow, job_name):
    result = None
    op_node = workflow.get_step (job_name)
    if op_node:
        logger.debug (f"   => exec: {job_name}")
        router = Router (workflow)
        await call_op (workflow, router, job_name, op_node)
    return result

class AsyncioExecutor:
    def __init__(self, workflow):
        self.workflow = workflow
    async def execute (self):
        while len(self.workflow.topsort) > len(self.workflow.execution.done):
            logger.debug ("loop...")
            for j in self.workflow.topsort:
                logger.debug (f" -eval: {j}")
                if j in self.workflow.execution.done or j in self.workflow.execution.running:
                    logger.debug (f"  -skip: {j}")
                    break
                dependencies = self.workflow.dependencies[j]
                if len(dependencies) == 0 or all ([ d in self.workflow.execution.done for d in dependencies ]):
                    logger.debug (f"  -run: {j}")
                    self.workflow.execution.done[j] = await exec_async(self.workflow, j)
            completed = []
            for job_name, promise in self.workflow.execution.running.items ():
                logger.debug (f"job {job_name} is ready:{promise.done()}") # failed:{promise.exception() is not None}")
                if promise.done ():
                    logger.debug (" -done: {job_name}")
                    completed.append (job_name)
                    self.workflow.set_result (job_name, promise.result ())
                    self.workflow.execution.done[job_name] = self.workflow.get_result (job_name)
                    if promise.exception ():
                        completed.append (job_name)
                        self.workflow.execution.failed[job_name] = promise.get ()
                        raise promise.exception ()
            for c in completed:
                logger.debug (f"removing {job_name} from running.")
                del self.workflow.execution.running[c]
            #time.sleep (2)
        return self.workflow.execution.done['return']

class CeleryDAGExecutor:
    def __init__(self, spec):
        self.spec = spec        
    def execute (self, async=False):
        ''' Dispatch a task to create the DAG for this workflow. '''
        model_dict = self.spec.json () #calc_dag(self.spec, inputs=self.inputs)
        model = json2model (model_dict)
        total_jobs = len(model.topsort)
        ''' Iterate over topologically sorted job names. '''
        while len(model.topsort) > 0:
            for j in model.topsort:
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
                logger.debug (f"job {job_name} is ready:{promise.ready()} failed:{promise.failed()}")
                if promise.ready ():
                    completed.append (job_name)
                    model.done[job_name] = promise.get ()
                    sink = model.get("workflow",{}).get(c,{})
                    sink['result'] = model.done[c]
                elif promise.failed ():
                    completed.append (job_name)
                    model.failed[job_name] = promise.get ()
            for c in completed:
                logger.debug (f"removing {job_name} from running.")
                del model.running[c]
        return model.done['return']
    
def setup_logging(
        default_path=os.path.join(os.path.dirname(__file__), 'logging.yaml'),
        default_level=logging.INFO,
        env_key='LOG_CFG'):
    """Setup logging configuration

    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

def start_task_queue ():
    """
    Use a separate process eventually.
    In the meantime, this will let us do parallel operations, the majority of which are I/O bound in any case.
    """
    code_path = os.path.join (os.path.dirname (__file__))
    celery_manager = CeleryManager (
        code_dir_to_monitor = code_path,
        celery_working_dir = code_path,
        celery_cmdline = "celery -A ros.dag.celery_app worker --loglevel=debug -c 3 -Q ros".split (" "))
    celery_manager.start ()

def main ():
    arg_parser = argparse.ArgumentParser(
        description='Ros Workflow CLI',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('-a', '--api', help="Execute via API instead of locally.", action="store_true")
    arg_parser.add_argument('-w', '--workflow', help="Workflow to execute.", default="mq2.ros")
    arg_parser.add_argument('-s', '--server', help="Hostname of api server", default="localhost")
    arg_parser.add_argument('-p', '--port', help="Port of the server", default="80")
    arg_parser.add_argument('-i', '--arg', help="Add an argument expressed as key=val", action='append', default=[])
    arg_parser.add_argument('-o', '--out', help="Output the workflow result graph to a file. Use 'stdout' to print to terminal.")
    arg_parser.add_argument('-l', '--lib_path', help="A directory containing workflow modules.", action='append', default=["."])
    arg_parser.add_argument('-n', '--ndex_id', help="Publish the graph to NDEx")
    arg_parser.add_argument('--validate', help="Validate inputs and outputs", action="store_true")
    args = arg_parser.parse_args ()

    setup_logging ()

    #start_task_queue ()
    
    """ Parse input arguments. """
    wf_args = { k : v for k, v in [ arg.split("=") for arg in args.arg ] }
    response = None
    if args.api:
        """ Invoke a remote API endpoint. """
        response = execute_rmote (workflow=args.workflow,
                                  host=args.server,
                                  port=args.port,
                                  args=wf_args)
    else:
        """ Execute the workflow in process. """
        celery = False
        if celery:
            """ Execute with celery. """
            executor = CeleryDAGExecutor (
                workflow=Workflow.get_workflow (workflow=args.workflow,
                                                inputs=wf_args,
                                                library_path=args.lib_path))
            response = executor.execute ()
        else:
            """ Execute via python async. """
            executor = AsyncioExecutor (
                workflow=Workflow.get_workflow (workflow=args.workflow,
                                                inputs=wf_args,
                                                library_path=args.lib_path))
            tasks = [
                asyncio.ensure_future (executor.execute ())
            ]
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.wait(tasks))
            
        """ NDEx output support. """
        if args.ndex_id:
            jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph")
            graph = [ match.value for match in jsonpath_query.find (response) ]
            logger.debug (f"{args.ndex_id} => {json.dumps(graph, indent=2)}")
            ndex = NDEx ()
            ndex.publish (args.ndex_id, graph)

    """ Output file. """
    if args.out:
        if args.out == "stdout":
            logger.debug (f"{graph_text}")
        else:
            with open(args.out, "w") as stream:
                stream.write (json.dumps(response, indent=2))
            
if __name__ == '__main__':
    main ()


# PYTHONPATH=$PWD/.. python dag/run_tasks.py --workflow workflows/workflow_one.ros -l workflows --arg disease_name="diabetest mellitus type 2"
