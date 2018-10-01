import requests
import json
from ros.operator import Operator

class Gamma(Operator):
    def __init__(self):
        self.robokop_url = 'http://robokop.renci.org/api/'
        self.max_results = 50
        
    def quick(self, question):
        url=f'http://robokop.renci.org:80/api/simple/quick/'
        response = requests.post(url,json=question)
        print( f"Return Status: {response.status_code}" )
        if response.status_code == 200:
            return response.json()
        return response

    def make_N_step_question(self, types,curies):
        question = {
            'machine_question': {
                'nodes': [],
                'edges': []
            }
        }
        for i,t in enumerate(types):
            newnode = {'id': i, 'type': t}
            if curies[i] is not None:
                newnode['curie'] = curies[i]
            question['machine_question']['nodes'].append(newnode)
            if i > 0:
                question['machine_question']['edges'].append( {'source_id': i-1, 'target_id': i})
        return question

    def extract_final_nodes(self, returnanswer):
        nodes = [{
            'node_name': answer['nodes'][2]['name'],
            'node_id': answer['nodes'][2]['id'] }
            for answer in returnanswer['answers']
        ]
        return pd.DataFrame(nodes)

    def module_wf1_mod3 (self, event):
        """ Execute module 3 of workflow one. """
        response = None

        #print (f"- - - - - - -- > {event.node['args']['conditions']}")
        print (f"- - - - - - -- > {event.conditions}")

        """ Query the graph for conditions. """
        diseases = event.context.graph.query (
            query = "match (a:disease) return  a",
            nodes = [ "a" ])
        assert len(diseases) > 0, "Found no diseases"

        """ Invoke the API. """
        disease = diseases [0]['id'] # TODO - multiplicity.
        api_call = f"{self.robokop_url}/wf1mod3/{disease}/?max_results={self.max_results}"
        response = requests.get(api_call, json={}, headers={'accept': 'application/json'})

        """ Process the response. """
        status_code = response.status_code
        #assert status_code == 200
        if not status_code == 200:
            print ("********** * * * GAMMA is broken. **********")
        return response.json() if status_code == 200 else event.context.graph_tools.kgs (nodes=[])

    def blah(self, graph):
        pass #curl -X GET "http://robokop.renci.org/api/wf1mod3a/DOID:9352/?max_results=5" -H "accept: application/json"
