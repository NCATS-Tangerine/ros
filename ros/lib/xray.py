import requests
import json
import sys
from ros.framework import Operator
from ros.lib.gamma import Gamma

class XRay (Operator):
    ''' Interact with the XRay reasoner. '''

    def __init__(self):
        self.url_str = "https://rtx.ncats.io/api/rtx/v1/query"
        self.gamma = Gamma ()
        
    def condition_expansion_to_gene_pathway_drug (self, event):
        response = None
        diseases = event.context.graph.query ("match (a:disease) return  a")
        assert len(diseases) > 0, "Found no diseases"

        """ Synonymize disease. Better than hard coding. Still needs further generalization. """
        doids = {}
        for d in diseases:
            syns = requests.get (f"https://onto.renci.org/synonyms/{d['id']}/").json ()
            for syn in syns:
                for s in syn['xref']:
                    if s.startswith ("DOID"):
                        print (f"-------> {s}")
                        doids[s] = s
        disease_id = [ d for d in doids.keys() ][0]
        
        ''' Execute the module. '''
        if len(diseases) > 0:
            response = requests.post(
                url = self.url_str,
                json = {
                    "query_type_id": "Q55",
                    "terms": {
                        "disease": disease_id
                    }
                }, 
                headers = { "accept": "application/json" })
            status_code = response.status_code
            assert status_code == 200
        return response.json() if response else None
    
    def wf1_mod1_mod2 (self, disease):
        ''' Execute workflow one modules 1 and 2. '''
        return self.condition_expansion_to_gene_pathway_drug (disease)
