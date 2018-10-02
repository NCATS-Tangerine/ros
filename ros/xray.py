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
        diseases = event.context.graph.query (
            query = "match (a:disease) return  a",
            nodes = [ "a" ])
        #print (diseases)
        assert len(diseases) > 0, "Found no diseases"
        
        ''' Execute the module. '''
        if len(diseases) > 0:
            #print (f"------------> {diseases}")
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
