import redis
from redisgraph import Node, Edge, Graph
from neo4j.v1 import GraphDatabase

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
    def __init__(self, graph, graph_name, host='localhost', port=6379):
        ''' Connect to Neo4J. '''
        uri = "bolt://localhost:7687"
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
        return self.graph.query (query)
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

    def query(self, query):
        """ Synonym for exec for read only contexts. """
        return self.exec(query)

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

    def create_relationship(self, id_a, type_a, properties, id_b, type_b):
        """ Create a relationship between two nodes given id and type for each end of the relationship and
        properties for the relationship itself. """
        relname = properties['name']
        rprops = ",".join([f""" {k} : "{v}" """ for k, v in properties.items() if not k == "name"])
        result = self.exec(
            f"""MATCH (a:{type_a} {{ id: "{id_a}" }})-[:{relname} {{ {rprops} }}]->(b:{type_b} {{ id : "{id_b}" }}) RETURN *""")
        return result if result.peek() else self.exec(
            f"""
            MATCH (a:{type_a} {{ id: "{id_a}" }})
            MATCH (b:{type_b} {{ id: "{id_b}" }})
            CREATE (a)-[:{relname} {{ {rprops} }}]->(b)""")
    
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
