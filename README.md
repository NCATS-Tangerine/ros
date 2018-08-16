# reasoner-tools


### Tools Available:

## Onto v2

## BioNames v2
All functions working as expected based on bionames v1 performance

## RoboQuery v1.1

Framework established for a system which uses ROBOKOP Builder to instantiate a graph 
and ROBOKOP Ranker to measure properties of that graph.

``` To test or try-out RoboQuery:
$ python -m venv reasoner-tools_env
$ source reasoner-tools_env/bin/activate
$ git clone git@github.com:NCATS-Tangerine/reasoner-tools
$ cd reasoner-tools
$ pip install greent/roboquery_requirements.txt
$ source deploy/setenv.sh
$ PYTHONPATH=$PWD python builder/api/roboquery_launcher.py
```
browse to localhost:5000/apidocs