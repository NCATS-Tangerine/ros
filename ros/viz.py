from greent.flow.graph import TranslatorGraphTools
import json
gt=TranslatorGraphTools()
g=gt.file_to_d3_json('test_graph.json')
with open('vis/g2.json', 'w') as s:
    json.dump(g,s,indent=2)
