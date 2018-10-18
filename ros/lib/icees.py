import json
import logging
import requests
import re
from time import sleep
from ros.framework import Operator
from ros.lib.bionames import Bionames

requests.packages.urllib3.disable_warnings()

logger = logging.getLogger("icees")
logger.setLevel(logging.WARNING)

class Icees(Operator):
    
    def __init__(self):
        super(Icees, self).__init__("icees")
        self.drug_suffix = [ "one", "ide", "ol", "ine", "min", "map" ]
        self.drug_names = [ "Prednisone", "Fluticasone", "Mometasone", "Budesonide", "Beclomethasone", "Ciclesonide", "Flunisolide", "Albuterol", "Metaproterenol", "Diphenhydramine", "Fexofenadine", "Cetirizine", "Ipratropium", "Salmeterol", "Arformoterol", "Formoterol", "Indacaterol", "Theophylline", "Omalizumab", "Mepolizumab", "Metformin" ]
        self.bionames = Bionames ()
        
    def parse_operator (self, spec, result={}):
        if isinstance (spec, list):
            for s in spec:
                result = self.parse_operator (s, result)
            return result
        key, operator, value = spec.split (" ")
        result[key] = {
            "operator" : operator,
            "value"    : int(value)
        }
        logger.debug (f"operator: {result}")
        return result
    
    def invoke(self, event):
        response = requests.post (
            url='https://icees.renci.org/1.0.0/patient/2010/cohort',
            json=self.parse_operator(event.cohort),
            headers = {
                "Content-Type" : "application/json"
            },
            verify = False).json ()

        print (f"--cohort response: {response}")
        cohort = response['return value']['cohort_id']

        if event.associations_to_all_features:
            request = {
                "feature" : self.parse_operator (event.associations_to_all_features['feature'],
                                                 result={}),
                "maximum_p_value" : event.associations_to_all_features['max_p_value']
            }

            url = f'https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/associations_to_all_features'
            logger.debug (f"---> {url}")
            logger.debug (f"--sending icees association_to_all_features request: {json.dumps(request, indent=2)}")
            
            response = requests.post(
                url = url,
                headers = {
                    "accept" : "application/json",
                    "Content-Type" : "application/json"
                },
                json = request,
                verify = False).json ()

            print (f"--Association response: {response}")

            """ Generalize when we have more than an asthma cohort. """
            asthma_id = "MONDO:0004979"
            nodes = [ {
                "id" : asthma_id,
                "type" : "disease"
            }]
            edges = []
            if 'return value' in response:
                for value in response['return value']:
                    logger.debug (f" value {value}")
                    if 'feature_b' in value:
                        feature_name = value['feature_b'].get ('feature_name', None)
                        logger.debug (f"feature_name: {feature_name}")
                        if feature_name and any([
                                v for v in self.drug_suffix if feature_name.endswith (v) ]):
                            chem_type = 'chemical_substance'
                            ids = self.bionames.get_ids (feature_name,
                                                         type_name=chem_type)
                            if len(ids) > 0:
                                logger.debug (f"Got ids for {feature_name}: {ids}")
                                for v in ids:
                                    v['name'] = v['label']
                                    del v['label']
                                    v['type'] = chem_type
                                    edges.append ({
                                        "type" : "icees_associated_with",
                                        "source_id" : v['id'],
                                        "target_id" : asthma_id,
                                        "edge_attributes" : value
                                    })
                                nodes = nodes + ids

        return event.context.graph_tools.kgs (
            nodes = nodes,
            edges = edges)
                                    
                                
                            




                            
'''
cq4 = {
    "AvgDailyPM2.5Exposure" : {
        "operator" : "<",
        "value" : 3
    },
    "TotalEDInpatientVisits" : {
        "operator" : "<",
        "value" : 2
    }
}
cq4 = {}

response = requests.post (
    url='https://icees.renci.org/1.0.0/patient/2010/cohort',
    json=cq4,
    headers = {
        "Content-Type" : "application/json"
    },
    verify = False).json ()

print(json.dumps(response, indent=2))

query = {
    "feature_a" : {
        "AvgDailyPM2.5Exposure" : {
            "operator" : "<",
            "value" : 3
        }
    },
    "feature_b":{
        "TotalEDInpatientVisits" : {
            "operator" : "<",
            "value" : 2
        }
    }
}
cohort = response['return value']['cohort_id']
#cohort = "COHORT:22"

print (f"https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/feature_association ")

response = requests.post (
    url = f"https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/feature_association",
    verify = False,
    headers = {
        "accept" : "application/json", #text/tabular",
        "Content-Type" : "application/json"
    },
    json = query)

print(json.dumps(response.json (), indent=2))

request = {
    "feature":{
        "TotalEDInpatientVisits": {
            "operator" : "<",
            "value" : 2
        }
    },
    "maximum_p_value" : 0.1
}
response = requests.post(
    url = 'https://icees.renci.org/1.0.0/patient/2010/cohort/COHORT%3A45/associations_to_all_features',
    headers = {
        "accept" : "application/json",
        "Content-Type" : "application/json"
    },
    json = request,
    verify = False).json ()
print (json.dumps (response, indent=2))
'''
