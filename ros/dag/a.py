import json
import requests

questions = {
    "drug-gene-anatomy-phenotype" : { # internal server error
        "edges": [
            {
                "source_id": 0,
                "target_id": 1
            },
            {
                "source_id": 1,
                "target_id": 2
            },
            {
                "source_id": 2,
                "target_id": 3
            }
        ],
        "nodes": [
            {
                "curie": "MESH:D000068877",
                "id": 0,
                "type": "drug"
            },
            {
                "id": 1,
                "type": "gene"
            },
            {
                "id": 2,
                "type": "anatomical_entity"
            },
            {
                "id": 3,
                "type": "phenotypic_feature"
            }
        ]
    },
    "disease-phenotype" : {
        "machine_question": {
            "edges": [
                {
                    "source_id": 0,
                    "target_id": 1
                }
            ],
            "nodes": [
                {
                    "curie": "MONDO:0004766",
                    "id": 0,
                    "type": "disease"
                },
                {
                    "id": 1,
                    "type": "phenotypic_feature"
                }
            ]
        }
    },
    "drug-gene-disease-phenotype" : { # internal server error
        "edges": [
            {
                "source_id": 0,
                "target_id": 1
            },
            {
                "source_id": 1,
            "target_id": 2
            },
            {
                "source_id": 2,
                "target_id": 3
            }
        ],
        "nodes": [
            {
                "curie": "MESH:D000068877",
                "id": 0,
                "type": "drug"
            },
            {
                "id": 1,
                "type": "gene"
            },
            {
                "id": 2,
                "type": "disease"
            },
            {
                "id": 3,
                "type": "phenotypic_feature"
            }
        ]
    },
    "disease-phenotype-anatomy" : {
        "machine_question": {
            "edges": [
                {
                    "source_id": 0,
                    "target_id": 1
                },
                {
                    "source_id": 1,
                    "target_id": 2
                }
            ],
            "nodes": [
                {
                    "curie": "MONDO:0004766",
                    "id": 0,
                    "type": "disease"
                },
                {
                    "id": 1,
                    "type": "phenotypic_feature"
                },
                {
                    "id": 2,
                    "type": "anatomical_entity"
                }
            ]
        }
    },
    "drug-gene-disease" : { # internal server error
        "machine_question": {
            "edges": [
                {
                    "source_id": 0,
                    "target_id": 1
                },
                {
                    "source_id": 1,
                    "target_id": 2
                }
            ],
            "nodes": [
                {
                    "curie": "MESH:D000068877",
                    "id": 0,
                    "type": "drug"
                },
                {
                    "id": 1,
                    "type": "gene"
                },
                {
                    "id": 2,
                    "type": "disease"
                }
            ]
        }
    }
}

url = "http://localhost:6011/api/now"

def answer (url, question):
    return requests.post (
        url = url,
        headers = {
            'accept' : 'application/json',
            'Content-Type' : 'application/json'
        },
        json = question).json()

def answer_all (url):
    for name, question in questions.items ():
        obj = answer (url, question)
        print (f"{name} : {len(obj)}")
        with open(f"{name}.json", "w") as stream:
            stream.write (json.dumps(obj, indent=2))

def answer_named (url, name):
    obj = answer (url, questions[name])
    print (f"{name} : {len(obj)}")

answer_named (url, "drug-gene-disease")
