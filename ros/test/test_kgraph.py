import json
import pytest
from ros.kgraph import Neo4JKnowledgeGraph

@pytest.fixture(scope='module')
def graph():
    ''' Create the graph. '''
    g = Neo4JKnowledgeGraph ()
    g.delete ()
    return g

def test_add_node(graph):
    ''' Test adding a node. '''
    graph.add_node (label="Obj", props={ "id" : "1", "type" : "2" })
    graph.add_node (label="Obj", props={ "id" : "3", "type" : "3" })

    result = graph.query ("""MATCH (a:Obj { id : "1" }) RETURN a""")
    print (result)
    assert len(result) == 1
    assert result[0]['type'] == "2"

    result = graph.query ("""MATCH (a:Obj { id : "3" }) RETURN a""")
    assert len(result) == 1
    assert result[0]['type'] == "3"
    
def test_add_edge(graph):
    ''' Add nodes. '''
    n0 = graph.add_node (label="Obj", props={ "id" : "1", "type" : "2" })
    n1 = graph.add_node (label="Obj", props={ "id" : "3", "type" : "3" })
    for x in range(0,100):
        n = graph.add_node (label="Obj", props={ "id" : str(x), "type" : "gene" })
        
    ''' Add an edge. '''
    graph.add_edge (n0['id'], 'related', n1['id'],
                    props={ 'type' : "related", 'x' : 1, 'y' : 2 })
    graph.commit ()
    
    result = graph.query ("""MATCH (a:Obj)-[r]->(b:Obj) RETURN a, r, b""")
    print (result)
    assert len(result) == 3
    assert result[1]['type'] == 'related'

    graph.delete ()

def test_delete (graph):
    graph.delete ()
