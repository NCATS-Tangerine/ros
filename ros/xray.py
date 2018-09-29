import requests
import json
import sys
from ros.operator import Operator

class XRay (Operator):
    ''' Interact with the XRay reasoner. '''

    def __init__(self):
        self.url_str = "https://rtx.ncats.io/api/rtx/v1/query"

    def condition_expansion_to_gene_pathway_drug (self, event):
        response = None

        ''' Query the graph for items of interest. disease ids. '''
        disease_ids = self.get_ids (self.get_nodes_by_type (
            graph = event.graph,
            target_type = "disease",
            query = "$.[*].answers.[*].nodes.[*]"))

        ''' Execute the module. '''
        if len(disease_ids) > 0:
            response = requests.post(
                url = self.url_str,
                json = {
                    "query_type_id": "Q55",
                    "terms": {
                        "disease": "DOID:9352" #disease_ids[0] #"DOID:9352"
                    }
                }, 
                headers = { "accept": "application/json" })
            status_code = response.status_code
            assert status_code == 200
        return response.json() if response else None
    
    def wf1_mod1_mod2 (self, disease):
        ''' Execute workflow one modules 1 and 2. '''
        return self.condition_expansion_to_gene_pathway_drug (disease)
