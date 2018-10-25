import json
import os
import requests
import logging
import logging.config
import networkx as nx
from node2vec import Node2Vec
from jsonpath_rw import jsonpath, parse
from ros.router import Router
from ros.workflow import Workflow
from ros.csvargs import CSVArgs

logger = logging.getLogger("client")
logger.setLevel(logging.WARNING)

class WorkflowResult:
    """
    Allows us to return a package containing the workflow specification 
    with the response received from the service.
    """
    def __init__(self, workflow, result):        
        self.workflow = workflow
        self.result = result
    def to_nx (self):
        """ Use Ros graph tools to compose a NetworkX object from the workflowanswer set. """
        return self.workflow.tools.answer_set_to_nx (self.result)
    
class Client:
    """ A Ros client to make getting a network from a workflow easier. """

    def __init__(self, url):
        """ Url is the location of the Ros server, eg: http://localhost:5002 """
        self.url = url
    
    def run (self, workflow, args={}, library_path=["."]):
        """ Execute the workflow remotely via a web API. """
        logger.debug (f"execute remote: {workflow} libpath: {library_path} args: {args} at {self.url}")

        """ Construct a workflow object, parse the workflow, and resolve imports - all locally. """
        workflow = Workflow (
            spec=workflow,
            inputs=args,
            libpath=library_path,
            local_connection=False)

        """ Execute the workflow remotely and return both the workflow object and the response we got. """
        return WorkflowResult (
            workflow = workflow,
            result = requests.post (
                url = f"{self.url}/api/executeWorkflow",
                json = {
                    "workflow" : workflow.spec,
                    "args"     : args
                }).json ())

def main ():
    
    workflow = 'workflows/workflow_one.ros'
    args = {
        "disease_name" : "type 2 diabetes mellitus",
    }
    libpath = [ 'workflows' ]
    
    """ general. """
    ros = Client (url="http://localhost:5002")
    response = ros.run (workflow=workflow,
                        args = args,
                        library_path = libpath)
    
    print (json.dumps (response.result, indent=2))

    graph = response.to_nx ()    
    for n in graph.nodes (data=True):
        print (n)



    n2v = Node2Vec (graph, dimensions=128, walk_length=80,
                    num_walks=10, p=1, q=1, weight_key='weight',
                    workers=1, sampling_strategy=None, quiet=False)
    model = n2v.fit ()

def main2 ():

    args_list = CSVArgs ('test.csv')
    workflow = 'workflows/m2m_models_v1.ros'
    libpath = [ 'workflows' ]

    """ Build graph. """
    g = nx.MultiDiGraph ()
    for args in args_list.vals: 
        ros = Client (url="http://localhost:5002")
        response = ros.run (workflow=workflow,
                            args = args,
                            library_path = libpath)
        
        print (json.dumps (response.result, indent=2))
        response_nx = response.to_nx ()
        print (f"read {len(response_nx.nodes())} nodes and {len(response_nx.edges())} edges.")
        g = nx.compose (g, response.to_nx ())

    """ Calulate node embeddings. """
    n2v = Node2Vec (g, dimensions=128, walk_length=80,
                    num_walks=10, p=1, q=1, weight_key='weight',
                    workers=1, sampling_strategy=None, quiet=False)
    model = n2v.fit ()
    
if __name__ == '__main__':
    main2 ()
