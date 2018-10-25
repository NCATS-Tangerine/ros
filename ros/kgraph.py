import json
import logging
import redis
#from redisgraph import Node, Edge, Graph
from neo4j.v1 import GraphDatabase
from neo4j.v1.types.graph import Node
from neo4j.v1.types.graph import Relationship
from ros.config import Config

logger = logging.getLogger("kgraph")
logger.setLevel(logging.WARNING)

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
        logger.debug ("deleting graph")
        self.graph.delete ()

class Neo4JKnowledgeGraph:
    ''' Encapsulates a knowledge graph. '''

    def __init__(self, host='localhost', port=7687):
        
        """ Load configuration. """
        self.config = Config ()

        """ Connect to Neo4J """
        host = self.config['neo4j']['host']
        username = self.config['neo4j']['username']
        password = self.config['neo4j']['password']
        uri = f"bolt://{host}:{port}"
        logger.debug (f"conneting to neo4j at {uri}")
        auth = None
        if isinstance(username,str) and isinstance(password,str):
            auth = (username, password)
            self._driver = GraphDatabase.driver (uri, auth=auth)
        else:
            self._driver = GraphDatabase.driver (uri)
        self.session = self._driver.session ()

    def add_node (self, label, props):
        """ Add a node to the graph. """
        return self.create_node (props, node_type=label)

    def add_edge (self, subj, pred, obj, props):
        """ Add an edge. """
        props['pred'] = pred
        logger.debug (f"+edge: ({subj}->{props}->{obj})")
        return self.create_relationship (subj, props, obj)

    def commit (self):
        """ Commit changes. """
        pass #self.session.commit ()

    def query (self, query):
        """ Query the graph. """
        result = self.graph.query (query)
        return [ node.properties for node in result ]
    
    def delete (self):
        """ Delete the entire graph. """
        self.exec ("match (a) detach delete a")
    
    def __del__ (self):
        """ Close the connection. """
        if self._driver:
            logger.debug ("Closing neo4j database connection.")
            self._driver.close ()
        
    def exec(self, command):
        """ Execute a cypher command returning the result. """
        return self.session.run(command)
    
    def node2json (self, rec):
        return {
            "id"          : rec.get("id", None),
            "name"        : rec.get("name", None),
            "description" : rec.get("description", None),
            "type"        : rec.get("type", None)
        }
    
    def edge2json (self, rec):
        return {
            "type" : rec.get ("type", None)
        }
    
    def query(self, query, nodes = [], edges = []):
        """ Synonym for exec for read only contexts. """
        response = []
        result = self.exec (query)
        for row in result:
            for k, v in row.items ():
                if isinstance (v, Node):
                    response.append (self.node2json (v))
                elif isinstance (v, Relationship):
                    response.append (self.edge2json (v))
                elif isinstance (v, str):
                    response.append (v)
        logger.debug (f"query: {response}")
        return response
    
    def get_node(self, properties, node_type=None):
        """ Get a ndoe given a set of properties and a node type to match on. """
        ntype = f":{node_type}" if node_type else ""
        properties = ",".join([f""" {k} : "{v}" """ for k, v in properties.items()])
        return self.exec(f"""MATCH (n{ntype} {{ {properties} }}) RETURN n""")

    def create_node(self, properties, node_type=None):
        """ Create a generic node given a set of properties and a node type. """
        id = properties['id']
        ntype = f":{node_type}" if node_type else ""
        props = ",".join([f""" n.{k}="{v}" """ for k, v in properties.items() if not k == 'id'])
        statement = f"""MERGE (n{ntype} {{ id : "{id}" }}) SET {props}"""
        logger.debug (f"create: stmt:{statement}")
        self.exec(statement)
        return properties
        
    def create_relationship(self, id_a, properties, id_b):
        """ Create a relationship between two nodes given id and type for each end of the relationship and
        properties for the relationship itself. """
        relname = properties['type'].replace('-','_')
        rprops = ",".join([f""" {k} : "{v}" """ for k, v in properties.items() if not k == "name"])
        result = self.exec(
            f"""MATCH (a {{ id: "{id_a}" }})-[:{relname} {{ {rprops} }}]->(b {{ id : "{id_b}" }}) RETURN *""")
        if not result.peek ():
            statement = f"""
                MATCH (a {{ id: "{id_a}" }})
                MATCH (b {{ id: "{id_b}" }})
                CREATE (a)-[:{relname} {{ {rprops} }}]->(b)"""
            result = self.exec (statement)
        return result

    def update (self, nodes=[], edges=[]):
        """ Update nodes and edges in the graph with properties from the inputs. """
        for n in nodes:
            props = ",".join([
                f""" s.{k} = "{v}" """
                for k, v in n.items()
                if not k == "id"
            ])
            statement = f"""MATCH (s {{ id : "{n['id']}" }}) SET {props} """
            self.exec (statement)

        # TODO: determine best way to represent hierarchical node properties.
        # TODO: analogous logic for updating edges.
        
