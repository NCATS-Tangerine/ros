from __future__ import absolute_import
import json
import logging
import time
#from ros.celery_app import app
from ros.workflow import Workflow
from ros.router import Router

logger = logging.getLogger("tasks")
logger.setLevel(logging.WARNING)

def json2workflow(json):
    model = Workflow (spec={ 'x' : 'y' })
    model.uuid = json['uuid']
    model.spec = json['spec']
    model.inputs = json['inputs']
    model.dependencies = json['dependencies']
    model.topsort = json['topsort']
    model.running = json['running']
    model.failed = json['failed']
    model.done = json['done']
    return model

def exec_operator(model, job_name):
    result = None
    wf = json2workflow (model)
    op_node = wf.spec.get("workflow",{}).get(job_name,{})
    if op_node:
        router = Router (wf)
        result = router.route (wf, job_name, op_node, op_node['code'], op_node['args'])
        wf.set_result (job_name, result)
    return result

async def exec_async (workflow, job_name):
    result = None
    logger.debug (f"running {job_name}")
    op_node = workflow.get_step (job_name)
    if op_node:        
        router = Router (workflow)
        result = await router.route (workflow, job_name, op_node, op_node['code'], op_node['args'])
        logger.debug (f"completed {job_name}")
        workflow.set_result (job_name, result)
    return result
