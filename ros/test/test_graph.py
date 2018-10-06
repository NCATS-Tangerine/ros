import json
import pytest
from networkx.readwrite import json_graph
from jsonpath_rw import jsonpath, parse
from ros.graph import TranslatorGraphTools
from ros.kgraph import KnowledgeGraph
from ros.kgraph import Neo4JKnowledgeGraph

@pytest.fixture(scope='module')
def graph_tools():
    return TranslatorGraphTools ()

'''
def test_from_file(graph_tools):
    graph = graph_tools.from_file ("test_graph.json")

    jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.node_list.[*]")
    nodes = [ match.value for match in jsonpath_query.find (graph) ]
    assert nodes[0]['id'] == 'DOID:9352'
    assert len(nodes) == 988
    
    jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.edge_list.[*]")
    edges = [ match.value for match in jsonpath_query.find (graph) ]
    edge = edges[0]
    assert edge["is_defined_by"] == "RTX"
    assert edge["provided_by"] == "BioLink"
    assert edge["source_id"] == "DOID:9352"
    assert edge["target_id"] == "HP:0011628"
    assert edge["type"] == "has_phenotype"
    assert len(edges) == 888

def test_file_to_nx(graph_tools):
    g = graph_tools.file_to_nx ("test_graph.json")
    data = json_graph.node_link_data(g)
    assert data['nodes'][0]['attr_dict']['name'] == 'DOID:9352'

def test_file_to_d3_json(graph_tools):
    g = graph_tools.file_to_d3_json ("test_graph.json")
    assert g['nodes'][0]['name'] == 'DOID:9352'
#    assert len(g['nodes']) == 988

def test_create_node (graph_tools):
    knowledge = Neo4JKnowledgeGraph ()
    result = knowledge.add_node (
        label = "label",
        props = {
            'nid'   : 'CURIE:123',
            'name'  : 'CURIE:123',
            "description" : "great",
            "type" : "type"
        })
    response = knowledge.query ("match (a:label) return a", nodes = [ "a" ])
    print (response[0])
    assert response[0]['id'] == 'CURIE:123'
    assert response[0]['description'] == 'great'
    assert response[0]['type'] == 'type'

def test_create_edge (graph_tools):
    knowledge = Neo4JKnowledgeGraph ()
    node1 = {
        'nid'  : 'CURIE:123x',
        'description' : 'great',
        "type" : "test_type"
    }
    node2 = {
        'nid'  : 'CURIE:123y',
        'description' : 'great',
        "type" : "test_type"
    }
    result = knowledge.add_node (label = "label", props = node1)
    result = knowledge.add_node (label = "label", props = node2)
    knowledge.add_edge (subj='CURIE:123x', pred='affects', obj='CURIE:123y', props={ 'type' : 'affects' })
    response = knowledge.query ("match (a:label { nid : 'CURIE:123x' })-[r:affects]->(b:label) return a,r,b")

    print (response)
    assert response[0]['id'] == 'CURIE:123x'
    assert response[0]['description'] == 'great'
    assert response[0]['type'] == 'test_type'
    
'''
def test_to_knowledge_graph (graph_tools):
    knowledge = Neo4JKnowledgeGraph ()
    graph_tools.to_knowledge_graph (
        in_graph = graph_tools.file_to_nx ("test_graph.json"),
        out_graph = knowledge)
    result = knowledge.query ("""MATCH (a) RETURN a""", nodes = [ "a" ])
    assert any([ r['id'] == 'CHEMBL.COMPOUND:CHEMBL2107774' for r in result ])

