#!/usr/bin/env python

import argparse
import json
import requests
import logging
from jinja2 import Template
import sys
from io import IOBase
from io import TextIOWrapper
from jsonpath_rw import parse
from ros.util import JSONKit

logger = logging.getLogger (__name__)
logger.setLevel (logging.DEBUG)

class GraphOp:
    
    def __init__(self, url):
        self.url = url
        
    def call (self, message):
        result = None
        
        """ Invoke the service; stash the response. """
        response = requests.post (
            url = self.url,
            json = message,
            headers = { "accept" : "application/json" })    
        if response.status_code == 200:
            logger.debug (f"Invoking service {self.url} succeeded.")
            result = response.json ()
        else:
            text = response.text[-800:] if len(response.text) > 800 else response.text
            logger.error (f"Service {self.url} failed with {text}")
            logger.error (f"Service {self.url} failed with error {response.status_code} and error: {text}")
        return result

class LifeCycle:
    
    def __init__(self):
        pass
    
    def from_file (self, path, required=False):
        value = None
        try:
            if isinstance(path,str):
                with open(path, "r") as stream:
                    value = json.load (stream)
                    #print (f"loaded {path}")
            elif isinstance(path, IOBase):
                value = json.load (path)
            else:
                raise ValueError(f"Received input path of unhandled type {type(path)}")
        except:
            if required:
                raise ValueError (f"Unable to load required file: {path}")
            else:
                #print (f"Unable to load file: {json.dumps(value, indent=2)}")
                logger.info (f"Unable to load file: {path}")
        return value

    def generate_questions (self, source, query, filter_val, question_template_path):
        questions = []
        with open(question_template_path, "r") as stream:
            template = Template (stream.read ())

            if query:
                jsonkit = JSONKit ()
                #print (f"=====================> query: {query} {json.dumps(source, indent=2)}, filter: {filter_val}")
                #print (f"=====================> query: {query} {type(source)}, filter: {filter_val}")
                selected = jsonkit.select (query=query,
                                           graph=source,
                                           target=filter_val)
                #print (f"=====================> {json.dumps(selected, indent=2)}")
                for n in selected:
                    #print (f"rendered template: {template.render (n)}")
                    questions.append (json.loads(template.render (n)))

                    # print()
                    # print('questions:', questions)
                    # print()



        #print (f"questions: {json.dumps(questions, indent=2)}")
        return questions
    
    def execute (self, question_path, source_path, query, filter_val, service, output):
        ''' Load the input question. '''
        question = self.from_file (question_path)
        source = self.from_file (source_path)

        questions = []
        if question and source:
            questions = self.generate_questions (source=source,
                                                 query=query,
                                                 filter_val=filter_val,
                                                 question_template_path=question_path)
        else:
            questions = [ question ]
        
        #print(questions)
        
        op = GraphOp (url = service)

        response = {}

        for q in questions:
            #print (f"question =====> {json.dumps(q, indent=2)}")
            response0 = op.call (q)
            #print (f"response0 {json.dumps(response0, indent=2)}")

            # print()
            # print('response0:', response0)
            # print()
            # print('length of response0:', len(response0))
            # print()
            # print('response0 type:', type(response0))
            # print()
            if isinstance(response0, dict):
                response.update (response0)
            else:
                print('skipping this response0, it is of the wrong type!')

        
        ''' Record the response. '''

        #print (f"output: {output}")
        if isinstance(output, TextIOWrapper):
            with open(output.name, "w") as stream:
                #print (f"response: {response} and ")
                if response:
                    
                    json.dump (response, stream, indent=2)
        else:
            if response:
                json.dump (response, output, indent=2)
        
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description='Ros CWL API',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('--question', help="question")
    arg_parser.add_argument('--service', help="service endpoint")
    arg_parser.add_argument('--source', help="source json object.")
    arg_parser.add_argument('--select', help="jsonpath selector into source object.")
    arg_parser.add_argument('--type', help="biolink-model type to use from previous source.")    
    arg_parser.add_argument('--output', help="knowledge_graph", type=argparse.FileType('w'))
    
    args = arg_parser.parse_args ()

    lifecycle = LifeCycle ()
    lifecycle.execute (service = args.service,
                       question_path = args.question,
                       source_path = args.source,
                       query=args.select,
                       filter_val=args.type,
                       output = args.output)
