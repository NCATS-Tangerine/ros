import json
import os
import pytest
from ros.util import Context
from ros.util import MaQ

@pytest.fixture(scope='module')
def maq():
    return MaQ ()

def test_gen_query_many_to_one (maq):
    context = Context ()
    questions = maq.parse ("""chem($drugs)->gene->disease($disease) """, context)
    drugs = context.resolve_arg ("$drugs")
    disease = context.resolve_arg ("$disease")
    
    for d in drugs:
        found = False
        for q in questions:
            for node in q['machine_question']['nodes']:
                found = node['curie'] == d                
                if found:
                    assert node['type'] == 'chemical_substance', "Incorrect biolink type for drug node"
                    break
            if found:
                break
        if found:
            break
        
def test_gen_query_many_to_many (maq):    
    context = Context ()
    questions = maq.parse ("""chem($drugs)->gene->disease($diseases) """, context)
    drugs = context.resolve_arg ("$drugs")
    diseases = context.resolve_arg ("$diseases")
    
    for drug in drugs:
        for disease in diseases: 
            drug_found = False
            disease_found = False
            for q in questions:
                nodes = q['machine_question']['nodes']
                drug_found = any (map (lambda n : n['curie'] == drug if 'curie' in n else False, nodes))
                disease_found = any (map (lambda n : n['curie'] == disease if 'curie' in n else False, nodes))
                if drug_found and disease_found:
                    break
            if not (drug_found and disease_found):
                raise ValueError (f"Unable to find a machine question linking drug {drug} and disease {disease}")
