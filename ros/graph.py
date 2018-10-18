import json
import logging
import random
import networkx as nx
import yaml
from flatdict import FlatDict
from jsonpath_rw import jsonpath, parse
from networkx.readwrite import json_graph
#from kgx import Transformer, NeoTransformer, PandasTransformer, NeoTransformer

logger = logging.getLogger("graph")
logger.setLevel(logging.WARNING)

class TranslatorGraphTools:
    """ Tools for working with graphs generally. """

    """ Migrate applicable pieces to KGX. """
    
    def __init__(self, name=None):
        self.name = name
        
    def from_file (self, file_name):
        """ Get an answer graph from disk. """
        result = None
        with open (file_name, "r") as stream:
            result = json.load (stream)
        return result
    
    def coalesce_node (self, node, all_nodes, seen):
        """ Merge all_nodes into node. """
        result = None
        logger.debug (node)
        n_id = node['id']
        if not n_id in seen:
            seen[n_id] = n_id
            for n in all_nodes:
                if n['id'] == node['id']:
                    node.update (n)
                    result = node
        return result
    
    def dedup_nodes(self, nodes):
        """ Get rid of duplicates. """
        seen = {}
        return [
            nn for nn in [
                self.coalesce_node (n, nodes, seen) for n in nodes
            ] if nn is not None
        ]
    
    def answer_set_to_nx (self, answers):
        """ Compose a NetworkX graph from an answer set. """
        result = nx.MultiDiGraph ()
        for answer in answers:
            g = self.to_nx (answer)
            result = nx.compose(result, g)
        return result
    
    def to_nx (self, graph):
        """ Convert answer graph to NetworkX. """
        
        """ Serialize node and edge python objects. """
        g = nx.MultiDiGraph()
        #logger.debug (f"graph: {json.dumps(graph, indent=2)}")
        jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.node_list.[*]") #.nodes.[*]")
        nodes = [ match.value for match in jsonpath_query.find (graph) ]
        nodes = self.dedup_nodes (nodes)
    
        jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.edge_list.[*]")
        edges = [ match.value for match in jsonpath_query.find (graph) ]
        for n in nodes:
            logger.debug (f"  --node> {n}")
            g.add_node(n['id'], attr_dict=n)
        for e in edges:
            logger.debug (f"  --edge> {e}")
            g.add_edge (e['source_id'], e['target_id'], attr_dict=e)
        return g
    
    def to_knowledge_graph (self, in_graph, out_graph, graph_label=None):
        """ Write a NetworkX graph to KnowledgeGraph. """
        id2node = {}
        for j, n in enumerate(in_graph.nodes (data=True)):
            logger.debug (f"node: {j}:{n}")
            i, obj = n
            if not 'attr_dict' in obj:
                continue
            attr = n[1]['attr_dict']

            """ encountered responses which randomly have numeric or curie as 'id' """
            if isinstance(attr['id'], int):
                """ yes, this also happens. """
                if isinstance(attr['name'], int):
                    continue
                if attr['name'].find (':') > 0:
                    attr['id'] = attr['name']
                    
            id2node[i] = out_graph.add_node (label=attr['type'], props=attr)
        for i, e in enumerate(in_graph.edges (data=True)):
            subj_id, obj_id, eprops = e
            attr = eprops['attr_dict']
            subj = id2node.get (subj_id,{}).get ('id', None)
            pred = attr['type']
            obj = id2node.get (obj_id,{}).get ('id', None)

            if subj == None or obj == None:
                #logger.warning (f"Unable to create edge for badly formed nodes: sub:{e[0]} obj:{e[1]}")
                continue
            if graph_label:
                attr['subgraph'] = graph_label
            logger.debug (f"({subj}-[{pred} {attr}]->{obj})")
            if subj and pred and obj:
                out_graph.add_edge (subj=subj,
                                    pred=pred,
                                    obj=obj,
                                    props=attr)
            
    def to_knowledge_graph_kgx (self, in_graph, out_graph, graph_label=None):
        """ Integrate kgx once it's ported to networkx 2.2 """
        id2node = {}
        for n in in_graph.nodes (data=True):
            node_id = n[0]
            id2node[node_id] = n[1]
            print (f"--- {n}")
            root = n[1]
            properties = root['attr_dict']
            properties['category'] = f"Node:{properties['type']}"
            if 'node_attributes' in properties:
                print (properties)
                flat = flattenDict (properties, delim='_')
                properties.update (flat)
                del properties['node_attributes']
            root.update (properties)
            del root['attr_dict']
            print (properties)
        for e in in_graph.edges (data=True):
            print (f"edge: {e}")
            attr = e[2]['attr_dict']
            attr['predicate'] = attr['type']
            attr['subject'] = attr['source_id']
            attr['object'] = attr['target_id']
            del attr['type']
            del attr['source_id']
            del attr['target_id']
        with open('config.yml', 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
            kgx = NeoTransformer (
                graph = in_graph,
                host = "localhost",
                ports = { 'bolt': 7687},
                username = cfg['neo4j']['username'],
                password = cfg['neo4j']['password']
            )
            kgx.save ()
        
    def file_to_nx (self, file_name):
        """ Read answer graph from file and convert to networkx. """
        return self.to_nx (self.from_file (file_name))
    
    def nx_to_d3_json(self, g):
        return json_graph.node_link_data(g)
    
    def file_to_d3_json(self, file_name):
        """ Read a file and convert to D3 compatible JSON. """
        g = self.nx_to_d3_json(self.file_to_nx(file_name))
        del g['directed']
        del g['multigraph']
        del g['graph']
        node_count = 0
        for n in g['nodes']:
            node_count = node_count + 1
            if 'attr_dict' in n:
                n['name'] = n['attr_dict']['name']
        new_edges = []
        for e in g['links']:
            e['weight'] = round(random.uniform(0.2, 0.98), 2)
            del e['key']
            new_edges.append (e)
        return g
    
    def kgs (self, nodes=[], edges=[]):
        """ Wrap nodes and edges in KGS standard. """
        return [
            {
                "result_list": [
                    {
                        "result_graph" : {
                            "node_list" : nodes,
                            "edge_list" : edges
                        }
                    }
                ]
            }
        ]

def flattenDict(d, result=None, delim='.'):
    if result is None:
        result = {}
    for key in d:
        value = d[key]
        if isinstance(value, dict):
            value1 = {}
            for keyIn in value:
                value1[delim.join([key,keyIn])]=value[keyIn]
            flattenDict(value1, result, delim)
        elif isinstance(value, (list, tuple)):
            for indexB, element in enumerate(value):
                if isinstance(element, dict):
                    value1 = {}
                    index = 0
                    for keyIn in element:
                        newkey = delim.join([key, keyIn, str(indexB)])
                        value1[newkey]=value[indexB][keyIn]
                        index += 1
                    for keyA in value1:
                        flattenDict(value1, result, delim)
                elif isinstance(element, (list, tuple)):
                    for i, value in enumerate (element):
                        list_key = delim.join (key, i)
                        if isinstance (value, dict):
                            value1 = {}
                            for keyIn in value:
                                k = delim.join ([ key, i, keyIn ])
                                value1[k]=value[keyIn]
                            flattenDict(value1, result, delim)
        else:
            result[key]=value
    return result



'''
  this response juggles which field contains the curie. eek.

      {
        "confidence": 2.32462976742824,
        "id": "6f05e17c-da07-4ad0-b304-b8e26a2f6016",
        "result_graph": {
          "node_list": [
            {
              "description": "type 2 diabetes mellitus",
              "id": "MONDO:0005148",
              "name": "type 2 diabetes mellitus",
              "type": "disease"
            },
            {
              "description": "triglyceride",
              "id": "CHEBI:17855",
              "name": "triglyceride",
              "type": "chemical_substance"
            },
            {
              "description": "superoxide",
              "id": "CHEBI:18421",
              "name": "superoxide",
              "type": "chemical_substance"
            },
            {
              "description": "DGAT1",
              "id": 76,
              "name": "HGNC:2843",
              "type": "gene"
            },
'''
