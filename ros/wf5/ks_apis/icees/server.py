"""Provide API for validating Translator Interchange API messages."""

import argparse
import json
import os
import yaml
import jsonschema
import requests
from flask import Flask, request, abort, Response
from flask_restful import Api, Resource
from flasgger import Swagger
from flask_cors import CORS

from iceesclient import ICEES

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

class ICEESAPI:
    def one_by_N (self, ):
        request = {
            "feature" : {
                "operator" : operator,
                "value"    : value
            },
            "maximum_p_value" : max_p_val
        }
        
        url = f'https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/associations_to_all_features'
        logger.debug (f"---> {url}")
        logger.debug (f"--sending icees association_to_all_features request: {json.dumps(request, indent=2)}")
        
        response = requests.post(
            url = url,
            headers = {
                "accept" : "application/json",
                "Content-Type" : "application/json"
            },
            json = request,
            verify = False).json ()
        
class ICEESQuery(Resource):
    """ ICEES Resource. """

    def cluster_cohorts (self, feature, threshold):
        
        return [ {
            "id" : 'cohort:22',
            "name" : 'x',
            "type" : "cohort"
        } for d in range(0,4) ]
    
    def post(self):
        """
        query
        ---
        tag: validation
        description: Query ICEES
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
        print (f"{json.dumps(request.json, indent=2)}")
        try:
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            print (f"ERROR: {str(error)}")
            abort(Response(str(error), 400))

#        inputs = request.json['knowledge_graph']['nodes']
#        print (f"inputs: {inputs}")

        cohort_id = "COHORT:22"
        feature_id = "EstResidentialDensity"
        value = "1"
        operator = ">"
        max_p_val = "0.5"

        icees = ICEES ()
        correlation = None
        if os.path.exists ("response.json"):
            with open("response.json", "r") as stream:
                correlation = json.load (stream)

        else:
            correlation = icees.feature_to_all_features (
                feature=feature_id,
                value=value,
                operator=operator,
                max_p_val=max_p_val,
                cohort_id=cohort_id)

            with open("response.json", "w") as stream:
                json.dump (correlation, stream, indent=2)
            
        graph = icees.parse_1_x_N (correlation)
        print (json.dumps (graph, indent=2))
        
        # "TotalEDInpatientVisits","<","2", "0.1")
        knowledge_graph = graph        
        print (f"kg: {json.dumps(knowledge_graph, indent=2)}")
        return knowledge_graph
    '''
        return {
            "question_graph" : {},
            "knowledge_graph" : knowledge_graph,
            "knowledge_mapping" : {}
        }, 200
    '''
    
api.add_resource(ICEESQuery, '/ICEESQuery')

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
