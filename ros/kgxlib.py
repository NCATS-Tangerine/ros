from kgx import Transformer, NeoTransformer, PandasTransformer, NeoTransformer

class KGraph:

    def __init__(self):
        self.ports = ports = {'bolt_port': 7687}
        self.xform = NeoTransformer (self.ports)
        
    def transform (self):
        self.xform.save_node ({
            "id"       : "AWESOME:23534",
            "name"     : "Really Great",
            "category" : "bioentity"
        })

if __name__ == '__main__':
    k = KGraph ()
    k.transform ()
    
# Monarch-Lite

'''
# Credentials can be found from 'Registry of Biolink-compatible Neo4 instances' spreadsheet
monarch_host = ''
ports = {'bolt': 7687}
monarch_username = ''
monarch_password = ''

# Initialize NeoTransformer
monarch_lite_transformer = NeoTransformer(host=monarch_host, ports=ports, username=monarch_username, password=monarch_password)

# Define filters
monarch_lite_transformer.set_filter("subject_category", "gene")
monarch_lite_transformer.set_filter("object_category", "disease")
monarch_lite_transformer.set_filter("edge_label", "contributes_to")

# Load nodes and edges from Monarch-Lite
start = 0
end = 5000
monarch_lite_transformer.load(start=start, end=end)
monarch_lite_transformer.report()

# Show the first 10 nodes from the networkx graph
monarch_lite_transformer.graph.nodes(data=True)[0:9]

# Show the first 10 edges from the networkx graph
monarch_lite_transformer.graph.edges(data=True)[0:9]

# Create a PandasTransformer, required for CSV export
pandas_transformer = PandasTransformer(monarch_lite_transformer.graph)

# export the networkx graph as CSV
pandas_transformer.save("monarch_lite_data.csv")

# You should see monarch_lite_data.csv.tar in your current folder.
'''
