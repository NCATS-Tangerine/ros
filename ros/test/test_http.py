import asyncio
import json
import os
import pytest
from ros.workflow import Workflow
from ros.app import AsyncioExecutor

def execute_workflow (workflow):
    executor = AsyncioExecutor (workflow=workflow)
    tasks = [ asyncio.ensure_future (executor.execute ()) ]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
    return tasks[0].result ()

def run_local_flow (path, inputs):
    workflow_path = os.path.join(os.path.dirname(__file__), path)
    workflow = Workflow (
        spec = workflow_path,
        inputs = inputs)
    execute_workflow (workflow)
    
def test_http ():
    run_local_flow (
        path = "test_wf_http.ros",
        inputs = {
            "disease_ids" : [ "MONDO:0005737" ],
            "drug_ids"    : [ "CHEMBL:CHEMBL941" ]
        })
