#!/usr/bin/env python

""" Flask REST API server """
import argparse
import asyncio
import os
import logging
import json
import time
import uvloop
from datetime import datetime
from flask import request
from flask_restful import Resource
from ros.api.api_setup import api, app
from ros.app import AsyncioExecutor
from ros.workflow import Workflow

""" Setup the async event loop. """
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()

logger = logging.getLogger("ros-api")


class ExecuteWorkflow(Resource):
    
    """ Workflow execution and monitoring logic. """
    
    def post(self):
        """
        ExecuteWorkflow
        ---
        tags: [executeWorkflow]
        summary: "Execute a Ros workflow."
        description: ""
        operationId: "executeWorkflow"
        consumes:
          - "application/json"
        produces:
          - "application/json"
        parameters:
          - in: "body"
            name: "body"
            description: "Workflow to be executed"
            required: true
            #schema:
            #    $ref: "#/definitions/Query"
        responses:
            200:
                description: "successful operation"
                #schema:
                #    $ref: "#/definitions/Response"
            400:
                description: "Invalid status value"
        """
        workflow_spec = request.json['workflow']        
        logger.debug(f"Received request {workflow_spec}.")
        print (f"Received request {json.dumps(workflow_spec,indent=2)} of type {type(workflow_spec)}.")

        executor = AsyncioExecutor (
            workflow=Workflow (spec=workflow_spec,
                               inputs=request.json['args']))
        response = loop.run_until_complete (executor.execute ())
        return response, 200

api.add_resource(ExecuteWorkflow, '/executeWorkflow')

if __name__ == '__main__':
    
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    arg_parser = argparse.ArgumentParser(
        description='Ros API',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('-d', '--debug', help="Debug.", action="store_false")
    arg_parser.add_argument('-p', '--port', help="Port of the server", default="80")
    args = arg_parser.parse_args ()
    
    server_host = '0.0.0.0'

    print (f"Serving Ros API on port: {args.port}")
    app.run(host=server_host,
            port=args.port,
            debug=False,
            use_reloader=True)
