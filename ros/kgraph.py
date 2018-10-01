import json
import redis
from redisgraph import Node, Edge, Graph
from neo4j.v1 import GraphDatabase
from neo4j.v1.types.graph import Node

class KnowledgeGraph:
    ''' Encapsulates a knowledge graph. '''
    def __init__(self, graph, graph_name, host='localhost', port=6379):
        ''' Connect to Redis. '''
        self.redis = redis.Redis(host=host, port=port)
        self.graph = Graph(graph_name, self.redis)
    def add_node (self, label, props):
        ''' Add a node to the graph. '''
        n = Node(label=label, properties=props)
        self.graph.add_node (n)
        return n
    def add_edge (self, subj, pred, obj, props):
        ''' Add an edge. '''
        e = Edge(subj, pred, obj, properties=props)
        self.graph.add_edge (e)
        return e
    def commit (self):
        ''' Commit changes. '''
        self.graph.commit ()
    def query (self, query):
        ''' Query the graph. '''
        return self.graph.query (query)
    def delete (self):
        ''' Delete the entire graph. '''
        self.graph.delete ()

class Neo4JKnowledgeGraph:
    ''' Encapsulates a knowledge graph. '''
    def __init__(self, host='localhost', port=7687):
        ''' Connect to Neo4J. '''
        uri = f"bolt://{host}:{port}"
        self._driver = GraphDatabase.driver (uri)
        self.session = self._driver.session ()
    def add_node (self, label, props):
        ''' Add a node to the graph. '''
        return self.create_node (props, node_type=label)
    def add_edge (self, subj, pred, obj, props):
        ''' Add an edge. '''
        props['pred'] = pred
        if not 'name' in props:
            props['name'] = 'none'
        return self.create_relationship (subj, props, obj)
    def commit (self):
        ''' Commit changes. '''
        pass #self.session.commit ()
    def query (self, query):
        ''' Query the graph. '''
        result = self.graph.query (query)
        return [ node.properties for node in result ]
    def delete (self):
        ''' Delete the entire graph. '''
        pass #self.graph.delete ()
    def __del__ (self):
        ''' Close the connection. '''
        self._driver.close ()
    #---------------------------------------
    def exec(self, command):
        """ Execute a cypher command returning the result. """
        return self.session.run(command)
    def process_node (self, rec):
        return {
            "id"          : rec.get("name", None),
            "nid"         : str(rec.get("id", None)),
            "description" : rec.get("description", None),
            "type"        : rec.get("type", None)
        }
    def query(self, query, nodes = [], edges = []):
        """ Synonym for exec for read only contexts. """
        result = self.exec (query)
        response = []
        for row in result:
            #print (f" {row}")
            r = self.process_node(row)
            #print (f" ...................|||| {r}")
            for node_name in nodes:
                response.append (self.process_node(row[node_name]))
        #print (f"=========> kgraph response: {response}")
        return response
    def get_node(self, properties, node_type=None):
        """ Get a ndoe given a set of properties and a node type to match on. """
        ntype = f":{node_type}" if node_type else ""
        properties = ",".join([f""" {k} : "{v}" """ for k, v in properties.items()])
        return self.exec(f"""MATCH (n{ntype} {{ {properties} }}) RETURN n""")

    def create_node(self, properties, node_type=None):
        """ Create a generic node given a set of properties and a node type. """
        ntype = f":{node_type}" if node_type else ""
        properties = ",".join([f""" {k} : "{v}" """ for k, v in properties.items()])
        return self.exec(f"""CREATE (n{ntype} {{ {properties} }}) RETURN n""")

    def create_relationship(self, id_a, properties, id_b):
        """ Create a relationship between two nodes given id and type for each end of the relationship and
        properties for the relationship itself. """
        relname = properties['name']
        rprops = ",".join([f""" {k} : "{v}" """ for k, v in properties.items() if not k == "name"])
        result = self.exec(
            f"""MATCH (a {{ id: "{id_a}" }})-[:{relname} {{ {rprops} }}]->(b {{ id : "{id_b}" }}) RETURN *""")
        return result if result.peek() else self.exec(
            f"""
            MATCH (a {{ id: "{id_a}" }})
            MATCH (b {{ id: "{id_b}" }})
            CREATE (a)-[:{relname} {{ {rprops} }}]->(b)""")

    def update (self, nodes=[], edges=[]):
        """ Update nodes and edges in the graph with properties from the inputs. """
        for n in nodes:
            #print (json.dumps (n, indent=2))
            props = ",".join([
                f""" s.{k} = "{v}" """
                for k, v in n.items()
                if not k == "id"
            ])
            statement = f"""MATCH (s {{ id : "{n['id']}" }}) SET {props} """
            self.exec (statement)

        # TODO: determine best way to represent hierarchical node properties.
        # TODO: analogous logic for updating edges.
        
