"""Provide API for validating Translator Interchange API messages."""

import argparse
import json
import yaml
import jsonschema
import requests
from flask import Flask, request, abort, Response
from flask_restful import Api, Resource
from flasgger import Swagger
from flask_cors import CORS
from jsonpath_rw import parse

app = Flask(__name__)

api = Api(app)
CORS(app)

filename = 'translator_interchange.yaml'
with open(filename, 'r') as file_obj:
    template = yaml.load(file_obj)
app.config['SWAGGER'] = {
    'title': 'Translator Interchange API Specification',
    'uiversion': 3
}
swagger = Swagger(app, template=template)

obj = None


class JSONKit:
    
    """ Query. """
    @staticmethod
    def select (query, obj):
        """ Execute a jsonpath_rw query on the given object. """
        jsonpath_query = parse (query)
        return [ match.value for match in jsonpath_query.find (obj) ]

class WF1Mod3(Resource):
    """Translator WF1Mod3. """

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
    
    def workflow_1_module_3 (self, diseases):
        return [
            {
                "id" : a[0],
                "name" : a[1],
                "type" : "disease",
                "description" : ""
            } for disease in diseases for s in self.get_genetic_versions (disease['id']) ]
    
    """ https://github.com/ncats/translator-workflows/blob/master/greengamma/workflow1/module1/module/WF1Mod1_Ontology.ipynb """
    def get_genetic_versions(disease):
        
        #These are identifiers signifying that the disease is genetic
        GENETIC_DISEASE=['MONDO:0021198','DOID:630','EFO:0000508','MONDO:0003847']
        
        durl=f'https://onto.renci.org/descendants/{disease}'
        response = requests.get(durl).json()
        genetic_set = set()
        for newmondo in response['descendants']:
            for gd in GENETIC_DISEASE:
                gurl = f'https://onto.renci.org/is_a/{newmondo}/{gd}/'
                gresponse = requests.get(gurl).json()
                if gresponse['is_a']:
                    lurl = f'http://onto.renci.org/label/{newmondo}/'
                    lresponse = requests.get(lurl).json()
                    label = lresponse['label']
                    genetic_set.add( (newmondo,label) )
        return genetic_set

    def post(self):
        """
        workflow_1_module_3
        ---
        tag: validation
        description: We're not actually doing anything with it.
        requestBody:
            description: Input message
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Message'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Successfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string


        """
        with open(filename, 'r') as file_obj:
            specs = yaml.load(file_obj)
        to_validate = specs['definitions']['Message']
        to_validate['definitions'] = specs['definitions']
        to_validate['definitions'].pop('Message', None)
        try:
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            abort(Response(str(error), 400))

        inputs = request.json['knowledge_graph']['nodes']
        print (f"inputs: {inputs}")
        knowledge_graph = self.kgs (nodes = self.workflow_1_module_3 (inputs))
        print (f"kg: {json.dumps(knowledge_graph, indent=2)}")
        return knowledge_graph, 200

api.add_resource(WF1Mod3, '/wf1mod3')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Short sample app')
    parser.add_argument('-port', action="store", dest="port", default=80, type=int)
    args = parser.parse_args()

    server_host = '0.0.0.0'
    server_port = args.port

    app.run(
        host=server_host,
        port=server_port,
        debug=False,
        use_reloader=True
    )
