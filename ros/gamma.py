import requests
import json

class Gamma:
    def __init__(self):
        self.ROBOCOP_API_BASE_URL = '"http://robokop.renci.org/api/'

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
        nodes = [{'node_name': answer['nodes'][2]['name'], 'node_id': answer['nodes'][2]['id']} for answer in returnanswer['answers']]
        return pd.DataFrame(nodes)

    def module_wf1_mod3 (self, disease):
        num_robocop_results = 50
        robocop_url_str = f"http://robokop.renci.org/api/wf1mod3/{disease}/?max_results={num_robocop_results}"
        #print (f"{robocop_url_str}")
        response_content = requests.get(robocop_url_str, json={}, headers={'accept': 'application/json'})
        status_code = response_content.status_code
        assert status_code == 200
        return response_content.json()

    def blah(self, graph):
        pass #curl -X GET "http://robokop.renci.org/api/wf1mod3a/DOID:9352/?max_results=5" -H "accept: application/json"
