import json
import requests
import re
from time import sleep
requests.packages.urllib3.disable_warnings()

cq4 = {
    "MaxDailyPM2.5Exposure" : {
        "operator" : ">",
        "value" : 1
    },
    "TotalEDInpatientVisits" : {
        "operator" : ">",
        "value" : 1
    }
}

response = requests.post (
    url='https://icees.renci.org/1.0.0/patient/2010/cohort',
    json=cq4,
    headers = {
        "Content-Type" : "application/json"
    },
    verify = False).json ()

print(json.dumps(response, indent=2))

query = {
    "feature_a" : {
        "MaxDailyPM2.5Exposure" : {
            "operator" : ">",
            "value" : 2
        }
    },
    "feature_b":{
        "TotalEDInpatientVisits" : {
            "operator" : ">",
            "value" : 1
        }
    }
}
cohort = response['return value']['cohort_id']

print (f"https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/feature_association ")

response = requests.post (
    url = f"https://icees.renci.org/1.0.0/patient/2010/cohort/{cohort}/feature_association",
    verify = False,
    headers = {
        "accept" : "application/json", #text/tabular",
        "Content-Type" : "application/json"
    },
    json = query)

print(json.dumps(response.json (), indent=2))