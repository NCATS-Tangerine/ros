import json
import os
import pytest
from ros.util import Syfur

@pytest.fixture(scope='module')
def syfur():
    return Syfur ()

def test_no_parameters (syfur):
    query = "match type=disease return id"
    expect = "match (obj{ type:'disease' }) return obj.id"
    assert syfur.parse (query) == expect, f"Failed to parse query {query}"

def test_multiple_parameters (syfur):
    query = "match type=chemical_substance id=CHEMBL.COMPOUND:CHEMBL595 return node_attributes"
    expect = "match (obj{ type:'chemical_substance',id:'CHEMBL.COMPOUND:CHEMBL595' }) return obj.node_attributes"
    assert syfur.parse (query) == expect, f"Failed to parse {query}"

def test_one_parameter (syfur):
    query = "match type=disease return id"
    expect = "match (obj{ type:'disease' }) return obj.id"
    assert syfur.parse (query) == expect, f"Failed to parse {query}"

def test_catch_delete (syfur):
    query = "match delete=x return id"
    success = False
    try:
        syfur.parse (query)
    except:
        success = True
    assert success, "Failed to detect unacceptable content."
    
def test_catch_delete (syfur):
    query = "match detach=x return id"
    success = False
    try:
        syfur.parse (query)
    except:
        success = True
    assert success, "Failed to detect unacceptable content."
