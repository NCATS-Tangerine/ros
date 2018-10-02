import json
import random
import networkx as nx
from jsonpath_rw import jsonpath, parse
from networkx.readwrite import json_graph

class TranslatorGraphTools:
    ''' Tools for working with graphs generally. '''
    def from_file (self, file_name):
        ''' Get an answer graph from disk. '''
        result = None
        with open (file_name, "r") as stream:
            result = json.load (stream)
        return result
    def coalesce_node (self, node, all_nodes, seen):
        ''' Merge all_nodes into node. '''
        result = None
        n_id = node['id']
        if not n_id in seen:
            seen[n_id] = n_id
            for n in all_nodes:
                if n['id'] == node['id']:
                    node.update (n)
                    result = node
        return result
    def dedup_nodes(self, nodes):
        ''' Get rid of duplicates. '''
        seen = {}
        return [
            nn for nn in [
                self.coalesce_node (n, nodes, seen) for n in nodes
            ] if nn is not None
        ]
    def to_nx (self, graph):
        ''' Convert answer graph to NetworkX. '''
        
        """ Serialize node and edge python objects. """
        g = nx.MultiDiGraph()
        #print (graph)
        #print (json.dumps(graph, indent=2))
        jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.node_list.[*]") #.nodes.[*]")
        nodes = [ match.value for match in jsonpath_query.find (graph) ]
        nodes = self.dedup_nodes (nodes)
        #print (f"nodes: {json.dumps(nodes,indent=2)}")
        #print (f"nodes: {len(nodes)}")
        node_id = { name : i for i, name in enumerate([ n['id'] for n in nodes ]) }
        for n in nodes:
            tmp = n['id']
            n['id'] = node_id[tmp]
            n['name'] = tmp            
        
        jsonpath_query = parse ("$.[*].result_list.[*].[*].result_graph.edge_list.[*]")
        edges = [ match.value for match in jsonpath_query.find (graph) ]
        for e in edges:
            tmp_src = e['source_id']
            tmp_dst = e['target_id']
            e['source_id'] = node_id[tmp_src]
            e['target_id'] = node_id[tmp_dst]
        for n in nodes:
            g.add_node(n['id'], attr_dict=n)
        for e in edges:
            g.add_edge (e['source_id'], e['target_id'], attr_dict=e)
        return g
    def to_knowledge_graph (self, in_graph, out_graph, graph_label=None):
        ''' Convert a networkx graph to Ros KnowledgeGraph. '''
        id2node = {}
        for j, n in enumerate(in_graph.nodes (data=True)):
            #print (f"{j}:{n}")
            i = n[0]
            attr = n[1]['attr_dict']
            #print (f"attr dict: {attr}")
            if graph_label:
                attr['subgraph'] = graph_label
            id2node[i] = out_graph.add_node (label=attr['type'], props=attr)
        for i, e in enumerate(in_graph.edges (data=True)):
            #print (f"{i}:{e}")
            attr = e[2]['attr_dict']
            subj = id2node[e[0]]
            pred = attr['type']
            obj = id2node[e[1]]
            if graph_label:
                attr['subgraph'] = graph_label
            #print (f"subj: {subj}")
            #print (f"  pred: {pred}")
            #print (f"    obj: {obj}")
            out_graph.add_edge (subj=id2node[e[0]],
                                pred=attr['type'],
                                obj=id2node[e[1]],
                                props=attr)
    def file_to_nx (self, file_name):
        ''' Read answer graph from file and convert to networkx. '''
        return self.to_nx (self.from_file (file_name))
    def nx_to_d3_json(self, g):
        return json_graph.node_link_data(g)
    def file_to_d3_json(self, file_name):
        g = self.nx_to_d3_json(self.file_to_nx(file_name))
        del g['directed']
        del g['multigraph']
        del g['graph']
        node_count = 0
        for n in g['nodes']:
            node_count = node_count + 1
            if 'attr_dict' in n:
                n['name'] = n['attr_dict']['name']
                #del n['attr_dict']
        #print (f"node count: {node_count}")
        new_edges = []
        for e in g['links']:
            e['weight'] = round(random.uniform(0.2, 0.98), 2)
            del e['key']
            if e['source'] < len(g['nodes']) and e['target'] < len(g['nodes']):
                new_edges.append (e)
        #g['links'] = new_edges
        return g
    def kgs (self, nodes=[], edges=[]):
        return [
            {
                "result_list": [
                    {
                        "result_graph" : {
                            "node_list" : nodes
                        }
                    }
                ]
            }
        ]
