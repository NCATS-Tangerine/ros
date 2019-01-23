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

response = None

class WF1Mod1(Resource):
    """Translator WF1Mod1. """

    def get_genetic_versions(self, disease):
        #These are identifiers signifying that the disease is genetic
        GENETIC_DISEASE=['MONDO:0021198','DOID:630','EFO:0000508','MONDO:0003847']

        durl=f'https://onto.renci.org/descendants/{disease}'
        print (f"----------> {durl}")
        response = requests.get(durl).json()
        genetic_set = set()
        for newmondo in response['descendants']:
            for gd in GENETIC_DISEASE:
                gurl = f'https://onto.renci.org/is_a/{newmondo}/{gd}/'
                print (gurl)
                gresponse = requests.get(gurl).json()
                if gresponse['is_a']:
                    lurl = f'http://onto.renci.org/label/{newmondo}/'
                    lresponse = requests.get(lurl).json()
                    label = lresponse['label']
                    genetic_set.add( (newmondo,label) )
        return genetic_set

    def workflow_1_module_1 (self, diseases):
        result = []
        s = []
        for disease in diseases:
            s = s + list(self.get_genetic_versions (disease['id']))
        return [ {
            "id" : d[0],
            "name" : d[1],
            "type" : "disease"
        } for d in s ]
    
    def post(self):
        """
        workflow_1_module_1
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

        print (f"{json.dumps(request.json, indent=2)}")

        inputs = request.json['knowledge_graph']['nodes']
        print (f"inputs: {inputs}")
        global response
        if response:
            knowledge_graph = response
        else:
            knowledge_graph = self.workflow_1_module_1 (inputs)
            response = knowledge_graph
            
        print (f"kg: {json.dumps(knowledge_graph, indent=2)}")
        return {
            "question_graph" : {},
            "knowledge_graph" : knowledge_graph,
            "knowledge_mapping" : {}
        }, 200

api.add_resource(WF1Mod1, '/wf1mod1')

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
