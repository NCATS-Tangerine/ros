import requests
import json
import argparse
requests.packages.urllib3.disable_warnings()

tabular_headers = {"Content-Type" : "application/json", "accept": "text/tabular"}
json_headers = {"Content-Type" : "application/json", "accept": "application/json"}

class IceesDefineCohort ():

    def __init__(self):
        pass
    
    def define_cohort(self, feature, value, operator):
        '''
        Here we take the three inputs which will define the ICEES cohort to call.
        '''
        self.cohort_definition = '{{"{0}": {{ "value": {1}, "operator": "{2}"}}}}'.format(feature, value, operator)
        return self.cohort_definition
    
    def query(self, cohort_definition):
        cohort_response = requests.post('https://icees.renci.org/1.0.0/patient/2010/cohort', data=self.cohort_definition, headers = json_headers, verify = False)               
        return cohort_response

    def run (self, feature, value, operator):
        cohort_definition = self.define_cohort(feature, value, operator)
        query = self.query(cohort_definition)
        query_json = query.json()
        return query_json['return value']

parser = argparse.ArgumentParser()
parser.add_argument("-ftr", "--feature", help="feature name")
parser.add_argument("-v", "--value", help="feature value")
parser.add_argument("-op", "--operator", help="feature operator")
args = parser.parse_args()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 3:
        icees_define_cohort = IceesDefineCohort()
        output = icees_define_cohort.run(args.feature, args.value, args.operator)
        if 'cohort_id' in str(output):
            print()
            print ('Cohort definition accepted')
            print(output)
            print()
    else:
        print("Expected script call is of the form: $python3 icees_caller.py -ftr <feature> -val <value> -op \<operator>")