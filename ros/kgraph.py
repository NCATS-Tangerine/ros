import json
import redis
from redisgraph import Node, Edge, Graph
from neo4j.v1 import GraphDatabase
from neo4j.v1.types.graph import Node
from neo4j.v1.types.graph import Relationship

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
        #print (f"({subj}->{props}->{obj})")
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
    def node2json (self, rec):
        print (f"process node: {rec}")
        print (f"process node: {rec['nid']}")
        print (f"process node: {rec['type']}")
        return {
            "id"          : rec.get("nid", None),
            "name"        : rec.get("nid", None),
            #"nid"         : str(rec.get("id", None)),
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
            print (f" row:--> {row}")
            print (f" row:--> {row.keys()}")
            for k, v in row.items ():
                if isinstance (v, Node):
                    response.append (self.node2json (v))
                elif isinstance (v, Relationship):
                    response.append (self.edge2json (v))
        print (f"=========> kgraph response: {response}")
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
        statement = f"""CREATE (n{ntype} {{ {properties} }}) RETURN n"""
        result = self.exec (statement)
        #print (f"--> {result}")
        n = [ n for n in result ][0]
        #print (f".......> {n}")
        n = self.node2json(n['n'])
        #print (f"________> {n}")
        return n
    
    def create_relationship(self, id_a, properties, id_b):
        """ Create a relationship between two nodes given id and type for each end of the relationship and
        properties for the relationship itself. """
        relname = properties['type']
        rprops = ",".join([f""" {k} : "{v}" """ for k, v in properties.items() if not k == "name"])
        q = f"""MATCH (a {{ nid: "{id_a}" }})-[:{relname} {{ {rprops} }}]->(b {{ nid : "{id_b}" }}) RETURN *"""
        result = self.exec(
            f"""MATCH (a {{ nid: "{id_a}" }})-[:{relname} {{ {rprops} }}]->(b {{ nid : "{id_b}" }}) RETURN *""")
        if not result.peek ():
            statement = f"""
                MATCH (a {{ nid: "{id_a}" }})
                MATCH (b {{ nid: "{id_b}" }})
                CREATE (a)-[:{relname} {{ {rprops} }}]->(b)"""
            result = self.exec (statement)
        return result

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
        
