import json
import pytest
from ros.kgraph import KnowledgeGraph

@pytest.fixture(scope='module')
def graph():
    ''' Create the graph. '''
    g = KnowledgeGraph (graph=None, graph_name='test')
    g.delete ()
    return g

def test_add_node(graph):
    ''' Test adding a node. '''
    graph.add_node (label="Obj", props={ "a" : "1", "b" : "2" })
    graph.add_node (label="Obj", props={ "a" : "3", "b" : "3" })
    graph.commit ()

    result = graph.query ("""MATCH (a:Obj { a : "1" }) RETURN a""")
    assert len(result.result_set) == 2

    result = graph.query ("""MATCH (a:Obj { a : "3" }) RETURN a""")
    assert len(result.result_set) == 2
    graph.delete ()
    
def test_add_edge(graph):
    ''' Add nodes. '''
    n0 = graph.add_node (label="Obj", props={ "a" : "1", "b" : "2" })
    n1 = graph.add_node (label="Obj", props={ "a" : "3", "b" : "3" })

    for x in range(0,100):
        n = graph.add_node (label="Obj", props={ "a" : str(x), "b" : "3" })
        
    ''' Add an edge. '''
    graph.add_edge (n0, 'related', n1, props={ 'x' : 1, 'y' : 2 })
    graph.commit ()
    
    result = graph.query ("""MATCH (a:Obj)-[r]->(b:Obj) RETURN a, r, b""")
    result.pretty_print ()
    assert len(result.result_set) == 2

    graph.delete ()

def test_delete (graph):
    graph.delete ()
