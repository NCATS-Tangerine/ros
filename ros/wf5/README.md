# Workflow 5 and CWL - Using this toolset to execute workflows with Common Workflow Language (CWL)

### $git clone git@github.com:NCATS-Tangerine/ros.git

#### create a new venv, use the following command if needed, then install requirements:

### $python3 -m venv YOUR_ENV_NAME_HERE
### $source YOUR_ENV_NAME_HERE/bin/activate
### $cd ros/ros/wf5

#### edit the file 'roscwlapi.cwl', line 6, to reflect the absolute path to the file 'roscwlapi.py' in your system. CWL does not easily accept relative paths or ENV variables for baseCommand

### $pip install -r requirements.txt

#### Get the ICEES query server running before executing the cwltool workflow:

### $cd ks_apis
### $PYTHONPATH=$PWD python3 icees/server.py

#### Ready to run the workflow, in a separate terminal window:

### $source YOUR_ENV_NAME_HERE/bin/activate
### $cd ros/ros/wf5
### $cwltool workflow_5_main.cwl workflow_5_EstResDens.yml

#### The above will run the workflow for clustering about the 'EstResidentialDensity' ICEES feature variable. In the (near-) future, other XYZ.yml files will become available for other ICEES feature variables. 'TotalEDInpatientVisits' is currently in the works.

#### The above operation will produce the following files in the current directory:
####    - icees_EstResidentialDensity.out.json
####    - gamma_EstResidentialDensity.out.json

#### The former is used to produce the latter through application of the gamma reasoner, ROBOKOP.

#### The latter can be copy-pasted into the http://robokopdb2.renci.org/apidocs/#/simple/post_api_simple_view_ endpoint, which will produce a string which looks like: 

#### "cdfa6222-1e97-4735-abe6-718950cb1e3a"

#### This string can then be substituted for {uid} in the following URL:

#### http://robokopdb2.renci.org/simple/view/cdfa6222-1e97-4735-abe6-718950cb1e3a

#### In the (near-) future, these last steps will be automated!