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
from types import SimpleNamespace
from ros.client import Client
from ros.router import Router
from ros.workflow import Workflow
from ros.lib.ndex import NDEx
from ros.tasks import exec_operator
from ros.util import JSONKit
from ros.util import LoggingUtil
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger("runner")
logger.setLevel(logging.WARNING)

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
    logger.debug (f"     call_op: {job_name}")
    return workflow.set_result (
        job_name,
        router.route (workflow, job_name, op_node, op_node['code'], op_node['args']))
    
async def exec_async (workflow, job_name):
    result = None
    op_node = workflow.get_step (job_name)
    if op_node:
        logger.debug (f"    -exec: {job_name}")
        router = Router (workflow)
        '''
        result = workflow.set_result (
            job_name,
            router.route (workflow, job_name, op_node, op_node['code'], op_node['args']))
        '''
        result = await call_op (workflow, router, job_name, op_node)
    return result

class AsyncioExecutor:
    """ Execute the workflow concurrently using Python async. """
    
    def __init__(self, workflow):
        """ Manage workflow execution. """
        self.workflow = workflow
        
    async def execute (self):
        """ A workflow execution coroutine. """
        while len(self.workflow.topsort) > len(self.workflow.execution.done):
            logger.debug ("scheduler")
            topsort = self.workflow.topsort.copy ()
            pending = topsort.copy ()
            for j in topsort:
                
                if j in self.workflow.execution.done or j in self.workflow.execution.running:
                    """ If running or done, it doesn't need further scheduling. """
                    continue
                
                dependencies = self.workflow.dependencies[j]
                logger.debug (f"   this:{j}, done:{[ d for d in self.workflow.execution.done.keys ()]} deps:{dependencies}")                
                if len(dependencies) == 0 or all ([ d in self.workflow.execution.done for d in dependencies ]):
                    """ Has no dependencies or they're all completed. Execute this task. Use Python async for concurrency. """
                    task = asyncio.ensure_future (exec_async (self.workflow, j))
                    self.workflow.execution.running[j] = task
                    pending.remove (j)
                    await task

            completed = []
            for job_name, promise in self.workflow.execution.running.items ():
                logger.debug (f"running job: {job_name} done:{promise.done()}")
                if promise.done ():
                    completed.append (job_name)
                    if promise.exception ():
                        completed.append (job_name)
                        self.workflow.execution.failed[job_name] = promise.get ()
                        raise promise.exception ()
                    else:
                        self.workflow.execution.done[job_name] = self.workflow.get_result (job_name)
            for c in completed:
                logger.debug (f"removing {job_name} from running.")
                del self.workflow.execution.running[c]
            time.sleep (1)
        return self.workflow.execution.done['return']

class CeleryDAGExecutor:
    def __init__(self, spec):
        self.spec = spec        
    def execute (self):
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
                    run_job (j, model, asynchronous=False)
                else:
                    ''' Iff all of this jobs dependencies are complete, run it. '''
                    if all ([ d in model.done for d in dependencies ]):
                        run_job (j, model, asynchronous=False)
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
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('-a', '--api', help="URL of the remote Ros server to use.", action="store_true")
    arg_parser.add_argument('-w', '--workflow', help="Workflow to execute.", default="workflow_one.ros")
    arg_parser.add_argument('-s', '--server', help="Hostname of api server", default="http://localhost:5002")
    arg_parser.add_argument('-i', '--arg', help="Add an argument expressed as key=val", action='append', default=[])
    arg_parser.add_argument('-o', '--out', help="Output the workflow result graph to a file. Use 'stdout' to print to terminal.")
    arg_parser.add_argument('-l', '--libpath', help="A directory containing workflow modules.", action='append', default=["."])
    arg_parser.add_argument('-n', '--ndex', help="Name of the graph to publish to NDEx. Requires valid ~/.ndex credential file.")
    arg_parser.add_argument('--validate', help="Validate inputs and outputs", action="store_true")
    args = arg_parser.parse_args ()

    LoggingUtil.setup_logging ()
    
    """ Parse input arguments. """
    wf_args = { k : v for k, v in [ arg.split("=") for arg in args.arg ] }
    response = None
    if args.api:

        """ Use the Ros client to run a workflow remotely. """
        client = Client (url=args.server)
        ros_result = client.run (workflow=args.workflow,
                                 args=wf_args,
                                 library_path=args.libpath)
        response = ros_result.result
        
    else:
        
        """ Execute locally via python async. """
        executor = AsyncioExecutor (
            workflow=Workflow.get_workflow (workflow=args.workflow,
                                            inputs=wf_args,
                                            library_path=args.libpath))
        tasks = [
            asyncio.ensure_future (executor.execute ())
        ]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
        
        response = tasks[0].result ()
        
    if args.ndex:
        """ Output to NDEx. """
        jsonkit = JSONKit ()
        graph = jsonkit.select ("$.[*][*].result_list.[*][*].result_graph", response)
        logger.debug (f"Publishing result as NDEx graph({args.ndex})=> {json.dumps(graph, indent=2)}")
        NDEx ()._publish (args.ndex, graph)

    if args.out:
        """ Write to a file, possibly standard ouput. """
        if args.out == "stdout":
            print (f"{json.dumps(response, indent=2)}")
        else:
            with open(args.out, "w") as stream:
                json.dump (response, stream, indent=2)
            
if __name__ == '__main__':
    main ()


# PYTHONPATH=$PWD/.. python dag/run_tasks.py --workflow workflows/workflow_one.ros -l workflows --arg disease_name="diabetest mellitus type 2"
