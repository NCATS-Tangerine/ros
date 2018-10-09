import requests
import json
import logging
from ros.framework import Operator

logger = logging.getLogger("gamma")
logger.setLevel(logging.WARNING)

class Gamma(Operator):
    def __init__(self):
        self.robokop_url = 'http://robokop.renci.org/api'
        self.max_results = 50
        
    def quick(self, question):
        url=f'http://robokop.renci.org:80/api/simple/quick/'
        response = requests.post(url,json=question)
        logger.debug ( f"Return Status: {response.status_code}" )
        if response.status_code == 200:
            return response.json()
        return response

    def make_N_step_question(self, types,curies):
        question = {
            'machine_question': {
                'nodes': [],
                'edges': []
            }
        }
        for i,t in enumerate(types):
            newnode = {'id': i, 'type': t}
            if curies[i] is not None:
                newnode['curie'] = curies[i]
            question['machine_question']['nodes'].append(newnode)
            if i > 0:
                question['machine_question']['edges'].append( {'source_id': i-1, 'target_id': i})
        return question

    def extract_final_nodes(self, returnanswer):
        nodes = [{
            'node_name': answer['nodes'][2]['name'],
            'node_id': answer['nodes'][2]['id'] }
            for answer in returnanswer['answers']
        ]
        return pd.DataFrame(nodes)

    def synonymize(self, nodetype,identifier):
        url=f'{self.robokop_url}/synonymize/{identifier}/{nodetype}/'
        #print (url)
        
        response = requests.post(url)
        #print( f'Return Status: {response.status_code}' )
        if response.status_code == 200:
            return response.json()
        return []

    def module_wf1_mod3 (self, event):
        """ Execute module 3 of workflow one. """
        response = None
        
        """ Query the graph for conditions. """
        #diseases = event.context.graph.query ("match (a:disease) return  a")
        diseases = event.context.jsonquery (
            query = "$.[*].result_list.[*].[*].result_graph.node_list.[*]",
            obj = event.conditions)
        assert len(diseases) > 0, "Found no diseases"

        """ Invoke the API. """
        disease = diseases[0]['name']
        api_call = f"{self.robokop_url}/wf1mod3a/{disease}/?max_results={self.max_results}"
        logger.debug (api_call)
        response = requests.get(api_call, json={}, headers={'accept': 'application/json'})
        
        """ Process the response. """
        status_code = response.status_code
        
        if not status_code == 200:
            logger.debug ("********** * * * GAMMA is broken. **********")
            
        return response.json() if status_code == 200 else event.context.graph_tools.kgs (nodes=[])

    def wf1_module3 (self, graph):
        pass #curl -X GET "http://robokop.renci.org/api/wf1mod3a/DOID:9352/?max_results=5" -H "accept: application/json"

    def gamma_query (self, context, node, question, inputs):
        ''' An interface to the Gamma reasoner. '''
        # validate.

        ''' Build the query. '''
        select = inputs['select']
        jsonpath_query = parse (select)
        source = inputs['from']

        logger.debug (f"    *job(gamma): select: {select} from: {source}")

        ''' Get the data source. '''
        operators = self.workflow.spec.get ("workflow", {})
        if not source in operators:
            logger.debug (f"Error: Source {source} not found in workflow.")
        if not "result" in operators[source]:
            if source in context.done:
                operators[source]["result"] = context.done[source]
        if not "result" in operators[source]:
            logger.debug (f"Error: Source {source} has not computed a result.")
        data_source = operators[source]["result"]
        
        ''' Execute the query. '''
        values = [ match.value for match in jsonpath_query.find (data_source) ]

        if 'where' in inputs and 'return' in inputs:
            return_col = inputs['return']
            collector = []
            where = inputs['where']
            filter_col, filter_value = where.split ('=')
            logger.debug (f"where: {filter_col} {filter_value}")
            columns = None
            filter_col_index = -1
            return_col_index = -1
            if "." in select:
                select_parts = select.split (".")
                last = select_parts[-1:][0]
                logger.debug (f"....{last}")
                if "," in last:
                    columns = last.split (",")
                    logger.debug (f".....{columns}")
                    for c, column in enumerate(columns):
                        logger.debug (f"column: {c} {column}")
                        if column == filter_col:
                            filter_col_index = c
                        if column == return_col:
                            return_col_index = c
            logger.debug (f"values: {values}")
            if filter_col_index > -1 and return_col_index > -1:
                for i in range(0, len(values), len(columns)):
                    actual_col_value = values[i + filter_col_index]
                    logger.debug (f"Actual col val {actual_col_value} at {i} + {filter_col_index}")
                    if actual_col_value == filter_value:
                        collector.append (values[ i + return_col_index ])
            else:
                logger.debug (f"Error: Must specify valid where clause and return together.")        
            values = collector

        if len(values) == 0:
            raise ValueError ("no values selected")

        # Read a cached local version.
        self.req = self.req + 1
        cache = False #True
        if cache:
            cache_file = f"ranker_{self.req}.json"
            if os.path.exists (cache_file):
                answer = None
                with open(cache_file, "r") as stream:
                    answer = json.loads (stream.read ())
            elif os.path.exists ("ranker.json"):
                answer = None
                with open("ranker.json", "r") as stream:
                    answer = json.loads (stream.read ())
            return answer

        ''' Write the query. '''
        machine_question = {
            "machine_question": {
                "edges" : [],
                "nodes" : []
            }
        }

        ''' Get the list of transitions and add an input node with the selected values. '''
        ''' If machine questions don't handle lists, we'll need to work around this. '''
        ''' Set the type to the type of the first element of transitions. Document. '''
        ''' ckc, aug 21: Indeed, MQs do not handle first node lists.'''
        transitions = question["transitions"]
        node_id = 0

        ''' Build a machine question. '''
        machine_question["machine_question"]["nodes"].append ({
            "curie" : values[0],
            "id" : node_id,
            "type" : transitions[0]
        })
        for transition in transitions[1:]:
            node_id = node_id + 1
            machine_question["machine_question"]["nodes"].append ({
                "id" : node_id,
                "type" : transition
            })
            machine_question["machine_question"]["edges"].append ({
                "source_id" : node_id - 1,
                "target_id" : node_id
            })
        logger.debug (f"Gamma machine question: {json.dumps(machine_question,indent=2)}")

        ''' Send the query to Gamma and handle result. '''
        query_headers = {
            'accept' : 'application/json',
            'Content-Type' : 'application/json'
        }

        logger.debug (f"executing builder query: {self.workflow.config.robokop_builder_build_url}")
        builder_task_id = requests.post(
            url = self.workflow.config.robokop_builder_build_url,
            headers = query_headers,
            json = machine_question).json()
        logger.debug (f"{json.dumps(builder_task_id,indent=2)}")
        task_id = builder_task_id["task id"]
        
        break_loop = False
        logger.debug (f"Waiting for builder to update the Knowledge Graph.")
        while not break_loop:
          time.sleep(1)
          url = f"{self.workflow.config.robokop_builder_task_status_url}{task_id}"
          builder_status = requests.get(url).json ()
          logger.debug (f"{builder_status} {url}")
          if isinstance(builder_status, dict) and builder_status['status'] == 'SUCCESS':
              break_loop = True
        
        ranker_url = f"{self.workflow.config.robokop_ranker_now_url}"
        logger.debug (f"ranker url: {ranker_url}")
        answer = requests.post (
            url = ranker_url,
            headers = query_headers,
            json = machine_question).text #json()

        try:
            obj = json.loads (answer)
            answer = obj
            file_name= f"ranker-{self.req}.json"
            with open(file_name, "w") as stream:
                stream.write (json.dumps (obj, indent=2))
        except:
            logger.debug (f"unable to parse answer: {answer}")
            traceback.print_exc ()
        
        return answer
