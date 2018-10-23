import argparse
import logging
from json import loads as json_loads
from json import dumps as json_dumps
from ros.app import AsyncioExecutor
from ros.workflow import Workflow
from ros.util import LoggingUtil
from sanic import Sanic
from sanic.response import html, json
from tornado.platform.asyncio import BaseAsyncIOLoop, to_asyncio_future
from sanic_openapi import swagger_blueprint, openapi_blueprint
from sanic_openapi import doc

"""
Models the web application programmer interface (API) to Ros knowledge network workflow engine.
"""

LoggingUtil.setup_logging (default_path="../logging.yaml")
logger = logging.getLogger("api")

app = Sanic(__name__)
app.blueprint(openapi_blueprint)
app.blueprint(swagger_blueprint)

""" Configure API metadata. """
app.config.API_VERSION = '1.0.0'
app.config.API_TITLE = 'Ros API'
app.config.API_DESCRIPTION = 'Ros Knowledge Network Workflow API'
app.config.API_TERMS_OF_SERVICE = 'https://github.com/NCATS-Tangerine/ros'
app.config.API_PRODUCES_CONTENT_TYPES = [ 'application/json' ]
app.config.API_CONTACT_EMAIL = 'scox@renci.org'

@app.post('/api/executeWorkflow/')
@doc.summary("""
   Executes a knowledge network workflow. For documentation on workflow syntax and how to subit to this endpoint, see the Ros documentation.
   It's linked above in 'Terms of Service'."""
)
async def executeWorkflow(request):
    
    """ Gather the workflow contents from the request. """
    workflow_spec = request.json['workflow']
    logger.debug(f"Received workflow execution request.")

    """ Build an async executor passing the workflow and its arguments. """
    executor = AsyncioExecutor (
        workflow=Workflow (
            spec=workflow_spec,
            inputs=request.json['args']))

    """ Execute the workflow coroutine asynchronously and return results when available. """
    return json(await executor.execute ())

def workaround_sanic_openapi_naming_issue ():
    """
    The framework renders two endpoint definitions for each actual one.
    Workaround until a better solution's found.
    """
    n = {}
    for k, v in app.router.routes_all.items ():
        if k[:-1] in n or f"{k}/" in n:
            continue
        n[k] = v
    app.router.routes_all = n
workaround_sanic_openapi_naming_issue ()

if __name__ == '__main__':

    LoggingUtil.setup_logging ()
    
    """ Process arguments. """
    arg_parser = argparse.ArgumentParser(
        description='Ros API',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('-d', '--debug', help="Debug.", action="store_false")
    arg_parser.add_argument('-p', '--port', help="Port of the server", default="8000")
    arg_parser.add_argument('--host', help="Server hostname", default="0.0.0.0")
    arg_parser.add_argument('--workers', help="Number of workers", type=int, default=1)
    args = arg_parser.parse_args ()

    """ Start the server. """
    app.run(host=args.host, port=args.port, debug=args.debug, workers=args.workers)
