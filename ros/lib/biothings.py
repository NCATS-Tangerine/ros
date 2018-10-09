import requests
import json
import os
from ros.framework import Operator

def annotate_drug(chembl_id):
    """
    Provide annotation for drug
    
    """
    query_template = 'http://mychem.info/v1/query?q=drugcentral.xref.chembl_id:{{chembl_id}}&fields=drugcentral'
    query_url = query_template.replace('{{chembl_id}}', chembl_id)
    results = {'annotate': {'common_side_effects': None, 'approval': None, 'indication': None, 'EPC': None}}
    api_response = requests.get(query_url).json()

    print (f"{query_url}")
    print (f"{json.dumps(api_response, indent=2)}")
    # get drug approval information from mychem
    approval = DictQuery(api_response).get("hits/drugcentral/approval")
    if approval:
        results['annotate']['approval'] = 'Yes'
    # get drug approved indication information
    indication = DictQuery(api_response).get("hits/drugcentral/drug_use/indication")
    if len(indication) > 0 and indication[0] and not isinstance(indication[0], list):
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication if 'snomed_full_name' in _doc]
    elif len(indication) > 0 and indication[0]:
        results['annotate']['indication'] = [_doc['snomed_full_name'] for _doc in indication[0] if 'snomed_full_name' in _doc]       
    # get drug established pharm class information
    results['annotate']['EPC'] = DictQuery(api_response).get("hits/drugcentral/pharmacology_class/fda_epc/description")
    # get drug common side effects
    side_effects = DictQuery(api_response).get("hits/drugcentral/fda_adverse_event")
    # todo
    '''
    if len(side_effects) > 0 and side_effects[0]:
        # only keep side effects with likelihood higher than the threshold
        results['annotate']['common_side_effects'] = [_doc['meddra_term'] for _doc in side_effects[0] if _doc['llr'] > _doc['llr_threshold']]
    '''
    return unlist(results)


"""
Helper functions
"""
def unlist(d):
    """
    If the list contain only one element, unlist it
    """
    for key, val in d.items():
            if isinstance(val, list):
                if len(val) == 1:
                    d[key] = val[0]
            elif isinstance(val, dict):
                unlist(val)
    return d

class DictQuery(dict):
    """
    Helper function to fetch value from a python dictionary
    """
    def get(self, path, default = None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    try:
                        val = [ v.get(key, default) if v else None for v in val]
                    except:
                        #todo
                        pass
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break;

        return val

def annotate_drugs_std_results(input_json_doc):
    """
    Annotate results from reasoner's standard output
    """
    for _doc in input_json_doc['result_list']:
        for _node in _doc['result_graph']['node_list']:
            if _node['id'].startswith('CHEMBL'):
                _drug = _node['id'].split(':')[-1]
                _node['node_attributes'] = annotate_drug(_drug)
    return data

class Biothings (Operator):
    """ Collection of modules provided by BioThings. """
    def __init__(self):
        """ Initialize the operator. """
        super(Biothings, self).__init__("biothings")
        
    def annotate_drugs (self, event):
        """ Query the shared graph for chemical substances. """
        drugs = event.context.graph.query (
            query = "match (c:chemical_substance) return  c",
            nodes = [ "c" ])

        """ Annotate each drug node. """
        for drug in drugs:
            annotations = None
            if not ':' in drug:
                continue
            compound_id = drug['id'].split (":")[1]
            cache_name = f"{compound_id}.cache"
            if not os.path.exists ('cache'):
                os.mkdir ("cache")
            cache_name = os.path.join ("cache", cache_name)
            if os.path.exists (cache_name):
                #print (f" opening {cache_name}")
                with open (cache_name, "r") as stream:
                    annotations = json.load (stream)
            else:
                annotations = annotate_drug (compound_id)
                with open (cache_name, "w") as stream:
                    json.dump (annotations, stream, indent=2)
            drug['node_attributes'] = annotations

        """ Return the results to be merged into the result graph. """
        event.context.graph.update (drugs)
        
        return event.context.graph_tools.kgs (nodes=drugs)

