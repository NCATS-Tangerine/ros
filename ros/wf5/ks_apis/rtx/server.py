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

obj = None

class WF1Mod1And2(Resource):
    """Translator WF1Mod1And2. """

    def workflow_1_modules_1_and_2 (self, diseases):
        url_str = "https://rtx.ncats.io/api/rtx/v1/query"

        doids = {}
        for d in diseases:
            syns = requests.get (f"https://onto.renci.org/synonyms/{d['id']}/").json ()
            for syn in syns:
                for s in syn['xref']:
                    if s.startswith ("DOID"):
                        doids[s] = s
        disease_id = [ d for d in doids.keys() ][0]
        
        ''' Execute the module. '''
        if disease_id is not None:
            response = requests.post(
                url = url_str,
                json = {
                    "query_type_id": "Q55",
                    "terms": {
                        "disease": disease_id
                    }
                }, 
                headers = { "accept": "application/json" })
            status_code = response.status_code
            assert status_code == 200

        return response.json() if response else None
    
    def post(self):
        """
        workflow_1_modules_1_and_2
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
        knowledge_graph = self.workflow_1_modules_1_and_2 (inputs)
        print (f"kg: {json.dumps(knowledge_graph, indent=2)}")
        return {
            "question_graph" : {},
            "knowledge_graph" : knowledge_graph,
            "knowledge_mapping" : {}
        }, 200
#        return knowledge_graph, 200

api.add_resource(WF1Mod1And2, '/wf1mod1and2')

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
