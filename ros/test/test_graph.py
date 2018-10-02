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

def test_from_file(graph_tools):
    graph = graph_tools.from_file ("test_graph.json")

    jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.node_list.[*]")
    nodes = [ match.value for match in jsonpath_query.find (graph) ]
    print (f"nodes {json.dumps(len(nodes), indent=2)}")
    assert len(nodes) > 0
    
    jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.edge_list.[*]")
    edges = [ match.value for match in jsonpath_query.find (graph) ]
    print (f"edges {json.dumps(len(edges), indent=2)}") 
    assert len(edges) > 0     

def test_file_to_nx(graph_tools):
    g = graph_tools.file_to_nx ("test_graph.json")
    data = json_graph.node_link_data(g)
    #print (json.dumps(data, indent=2))

def test_file_to_d3_json(graph_tools):
    g = graph_tools.file_to_d3_json ("test_graph.json")
    return g

def test_to_knowledge_graph (graph_tools):
    #knowledge = KnowledgeGraph (graph=None, graph_name="test")
    knowledge = Neo4JKnowledgeGraph () #graph=None, graph_name="test")
    graph_tools.to_knowledge_graph (
        in_graph = graph_tools.file_to_nx ("test_graph.json"),
        out_graph = knowledge)
    print (f"---------> q1")
    result = knowledge.query ("""MATCH (a)-->(b) RETURN a, b""")
    #result.pretty_print ()
