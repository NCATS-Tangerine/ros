import json
import networkx as nx
from jsonpath_rw import jsonpath, parse
import os
import sys
from ndex2 import create_nice_cx_from_networkx
from ndex2.client import Ndex2

class NDEx:

   """ An interface to the NDEx network catalog. """ 
   def __init__(self, uri="http://public.ndexbio.org"):
       
      ndex_creds = os.path.expanduser("~/.ndex")
      if os.path.exists (ndex_creds):
         with open(ndex_creds, "r") as stream:
            ndex_creds_obj = json.loads (stream.read ())
            print (f"connecting to ndex as {ndex_creds_obj['username']}")
            account = ndex_creds_obj['username']
            password = ndex_creds_obj['password']
      else:
          raise ValueError ("No ndex credentials found.")
      
      self.uri = uri
      self.session = None
      self.account = account
      self.password = password
      try:
         self.session = Ndex2 (uri, account, password)
         self.session.update_status()
         networks = self.session.status.get("networkCount")
         users = self.session.status.get("userCount")
         groups = self.session.status.get("groupCount")
         print(f"session: networks: {networks} users: {users} groups: {groups}")
      except Exception as inst:
         print(f"Could not access account {account}")
         raise inst
      
   def publish (self, name, graph):
      """ Save a networkx graph to NDEx. """
      assert name, "A name for the network is required."

      """ Serialize node and edge python objects. """
      g = nx.MultiDiGraph()
      print (f"{json.dumps (graph, indent=2)}")

      
      jsonpath_query = parse ("$.[*].node_list.[*].[*]")
      nodes = [ match.value for match in jsonpath_query.find (graph) ]
      print (f"{json.dumps(nodes, indent=2)}")

      jsonpath_query = parse ("$.[*].edge_list.[*].[*]")
      edges = [ match.value for match in jsonpath_query.find (graph) ]
      print (f"{json.dumps(edges, indent=2)}")
      
      for n in nodes:
         g.add_node(n['id'], attr_dict=n)
      for e in edges:
         print (f"  s: {json.dumps(e,indent=2)}")
         g.add_edge (e['source_id'], e['target_id'], attr_dict=e)

      """ Convert to CX network. """
      nice_cx = create_nice_cx_from_networkx (g)
      nice_cx.set_name (name)
      print (f" connected: edges: {len(g.edges())} nodes: {len(g.nodes())}")
      print (nice_cx)

      """ Upload to NDEx. """
      upload_message = nice_cx.upload_to(self.uri, self.account, self.password)
