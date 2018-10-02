from __future__ import absolute_import
import json
import time
from ros.dag.celery_app import app
from ros.workflow import Workflow
from ros.router import Router

def json2model(json):
    model = Workflow (spec={ "a" : "b"})
    model.uuid = json['uuid']
    model.spec = json['spec']
    model.inputs = json['inputs']
    model.dependencies = json['dependencies']
    model.topsort = json['topsort']
    model.running = json['running']
    model.failed = json['failed']
    model.done = json['done']
    return model

@app.task(bind=True, queue="rosetta")
def calc_dag (self, workflow_spec, inputs):
    return Workflow (workflow_spec, inputs=inputs).json ()

@app.task(bind=True, queue="rosetta")
def exec_operator(self, model, job_name):
    result = None
    wf = json2model (model)
    op_node = wf.spec.get("workflow",{}).get(job_name,{})
    if op_node:
        router = Router (wf)
#        result = router.route (wf, job_name, op_node, op_node['code'], op_node['args'])
        result = router.route (wf, job_name, op_node, op_node['code'], op_node['args'])
        wf.set_result (job_name, result)
    return result
