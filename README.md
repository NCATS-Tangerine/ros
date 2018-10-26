
<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/ros.png" width="40%"></src>

## Overview

Ros executes graphs of queries to cooperatively compose knowledge networks.

While the language provides common constructs supporting variables, modularity, extensibility, templates, and a type system, it is targeted at the distinctive challenges of creating **highly detailed knowledge graphs enabling reasoning and inference**.

### Usage

Running a workflow locally from the command line produces output like this:

<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/run.png" width="100%"></src>

And builds this knowledge graph:

<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/wf1_output.png" width="100%"></src>

- [Overview](#overview)
  * [Usage](#usage)
- [Language Reference](#language-reference)
  * [Overview](#overview-1)
  * [Variables](#variables)
  * [Operators](#operators)
  * [Graphs](#graphs)
  * [Metadata](#metadata)
  * [Templates](#templates)
  * [Modules](#modules)
- [Putting it All Together](#putting-it-all-together)
  * [1. Define A Template](#1-define-a-template)
  * [2. Optionally Model Input and Output Types](#2-optionally-model-input-and-output-types)
  * [3. Example Workflows](#3-example-workflows)
- [Execution](#execution)
- [Getting Started](#getting-started)
  * [Docker](#docker)
    + [Requirements](#requirements)
    + [Start the API Containers](#start-the-api-containers)
  * [Usage - Command Line](#usage---command-line)
  * [Usage - Programmatic](#usage---programmatic)
  * [Install](#install)
  * [NDEx](#ndex)
  * [Help](#help)

## Language Reference

### Overview

A workflow is a series of steps.
Steps can reference the output of previous steps.
In general they have access to a shared graph.
They can also exchange sub-graphs.
Steps can have associated metadata describing their allowed input and output types.

Workflows compute a directed acyclic graph (DAG) modeling job dependencies which are then executed in the order indicated by a topological sort of the DAG.

### Variables

Variables passed to the workflow at the command line or via the API can be resolved dynamically. In this example, $disease_name refers to an argument provided by the execution context to this workflow. The provided value will be substituted at runtime. 

In the example below we use a SQL like syntax to select disease identifiers into the `disease_ids` variable. Subsequent jobs can interact with the list of identifiers by way of the variable.

The `code` tag tells the engine to execute the bionames module.

The `args` section lists inputs to this operator.

```
  naming:
    doc: Resolve names to ontology identifiers.
    code: bionames
    args:
      query:
        - select $disease_name from disease as disease_ids
        - select $drug_name from drug as drug_ids
        - select "particulate matter" from chemical_substance as particulate_matter_ids
```

### Operators

The workflow is organized around graph operators. Each has access to all facilities of the Ros framework including the shared graph.

In general, workflow jobs have the following fields:

  * **doc**: A documentation string.
  * **code**: The name of a component providing functionality.
  * **args**: Arguments to the operator.

Ros currently provides the following core operators:

* **requests**: Provides generic HTTP capabilities.
* **union**: Unions two or more results into one object.

### Graphs

Ros provides graphs in two basic modalities:

* **Results**: Results of previous workflow steps can be referenced as variables passed to subsequent steps. This graph can be queried using JSON Path query syntax. The following example uses the json select facility in the Ros framework to query a variable called *condition*:
   ```
   diseases = event.select (
            query = "$.[*].result_list.[*].[*].result_graph.node_list.[*]",
            obj = event.conditions)
   ```
* **Shared**: A shared graph, accessible with the Cypher query language is available to all operators. This example uses the Ros framework's cypher query on the shared graph with biolink-model concepts.
   ```
   diseases = event.context.graph.query ("match (a:disease) return  a")
   ```
   
Each operator receives an event object provided by the Ros framework. The event provides framework services including the shared graph, graph manipulation tools, and arguments to the invocation of the operator.

These facilities allow the operator to query the graphs before executing their main logic and to update it as well.

### Metadata

The language supports a metadata capability to enable modules to specify their inputs and outputs.

Inputs support these tags:

* **doc**: Documentation
* **type**: Types are currently derived from a standard library but in the future will be extensible and composable.
* **required**: Whether or not the argument is required.

Outputs support these tags:
* **doc**: Documentation.
* **type**: Type of the returned object.

The use of metadata is optional.

### Templates

Templates allow extension of the language by specializing existing library functions into new capabilities through composition. Templates are defined in a template section separate from the workflow proper. They can also be defined in separate, reusable modules.

### Modules

External modules can be loaded via the `import` tag.

A library path like those featured in other high level programming languages governs where libraries are loaded from.

### Automated Validation

When a workflow has run, we'd like to run validations that test the integrity of the answer we got. In this first Ros version, we support a limited form of automated validation. The limitations are motivated by making Ros secure. Since we execute queries remotely, it's not realistic to run arbitrary graph queries posted from clients on the internet. Instead, we provide a limited query syntax that still allows us to do a lot of validation. The query syntax is called Syfur - a less capable query system reminiscent of Cypher.

The example below from workflow_one shows Syfur's usage.

  ```
  automated_validation:
    doc: |
      Automated Validation
         We can test the knowledge network with constraints including all, match, and none.
         The depends arg ensures the validation runs only after the graph is built.
         Each test has a name, documentation, a query, and an operator defining the constraint to enforce
      Syfur
         A principal virtue of Ros is the ability to remotely execute workflows.
         To make this possible, it must be secured against remote code execution attacks
         This includes cypher injection.
         It may be possible to accomplish some of this in other ways, but for now, we provide Syfur
         Syfur is a restricted DSL that translates to a subset of Cypher. See examples below.
    code: validate
    args:
      depends: $biothings_module_4_and_5
      tests:
        test_type_2_diabetes_exists:
          doc: Ensure type 2 diabetes mellitus and other conditions are present.
          items: "match type=disease return id"
          all: [ "OMIM:600001", "MONDO:0005148", "DOID:9352" ]
        test_pioglitazone:
          doc: Test attributes of a specific chemical. Ensure type 2 diabetes mellitus is present.
          items: "match type=chemical_substance id=CHEMBL.COMPOUND:CHEMBL595 return node_attributes"
          match:
            - .*Thiazolidinedione.*
            - ".*{'name': 'EPC', 'value': 'Peroxisome Proliferator Receptor gamma Agonist'}.*"
        test_absence_of_something:
          doc: Verify there is none of something in our graph.
          items: "match return id"
          none: [ 'BAD:123' ]
  ```
   
## Putting it All Together

Here's a usage example to put all of this in context.

### 1. Define A Template

We begin with the common use case of converting user supplied text into ontology identifiers. We create a template task for this purpose.

* It extends the builtin `get` http operator and sets the `pattern` argument to a defined value.
* It's saved to a file called `bionames.ros` in a directory that's on the library path.

The bionames template is now a reusable component that can be imported into a variety of workflows.

### 2. Optionally Model Input and Output Types

Though currently optional, the template also specifies

* The `meta` tag describes metadata about the operator.
* The `main` operator is used when no sub-operators are specified.
* Each operator has input and output sections.
* The **input** section specifies a list of input values.
* Each may have `doc`, `type`, and `required` tags.
* The **output** section may contain `doc` and `type` tags.
* In both cases, values of `type` must (currently) come from the Ros standard library, described elsewhere.

```
doc: |
  This module defines a reusable template.
  It can be imported into other workflows via the import directive.

templates:

  bionames:
    doc: |
      This template extends the built in get operator.
    code: get
    args:
      pattern: 'https://bionames.renci.org/lookup/{input}/{type}/'
    meta:
      main:
        args:
          input:
            doc: The name of the object to find identifiers for.
            type: string
            required: true
          type:
            doc: The intended biolink_model type of the resulting identifiers.
            type: biolink_model
            required: true
        output:
          doc: A Translator standard knowledge graph.
          type: knowledge_graph_standard
```

The `biolink_model` and `knowledge_graph_standard` types are currently modeled directly in the Ros [standard library](https://github.com/NCATS-Tangerine/ros/blob/master/ros/stdlib.yaml):
```
types:
  string :
    doc: A primitive string of characters.
    extends: primitive
  biolink_model:
    doc: An element from the Biolink-model 
    extends: string
  knowledge_graph_standard:
    doc: A Translator knowledge graph standard (KGS) knowledge graph.
    extends: primitive
```

### 3. Example Workflows

To get started with the language, see the [Translator](https://github.com/NCATS-Tangerine/ros-translator/tree/master/translator/ros/workflows) workflows.

## Execution

For all workflows, the engine builds a directed acyclic graph (DAG) of jobs by examining each job to determine its dependencies.

A topological sort of the jobs provides the execution order.

Execution is asynchronous. To the extent you subscribe to the [semantic distinction between 'concurrent' and 'parallel'](https://softwareengineering.stackexchange.com/questions/190719/the-difference-between-concurrent-and-parallel-execution) workflow execution is concurrent but not parallel.

The current implementation uses Python's [asyncio](https://docs.python.org/3/library/asyncio.html). This means multiple operations are able to make progress during the same time window. But it does not mean that the operations literally execute (run CPU operations) simultaneously. The current profile of operations is I/O bound rather than CPU bound so this approach is likely to be enough for a while. Several tasks can wait for an HTTP request to return while others use the processor to handle results.

The API also handles requests asynchronously using [Sanic](https://github.com/huge-success/sanic) and [Tornado](https://www.tornadoweb.org/en/stable/) 

## Getting Started

### Docker

#### Requirements

  * Docker - i.e. the Docker servie is running.
  * Docker Compose (included with Docker on Mac)
  * Git
  * Ports 7474, 7687, 6379, and 5002 available
  * Python 3.7.x

#### Start the API Containers

This will run docker compose which, in turn, will start redis, neo4j, and Ros API containers.

```
git clone git@github.com:NCATS-Tangerine/ros.git
cd ros/deploy
./rosctl up
```

### Usage - Command Line

  * Connect to the [local Neo4J](http://localhost:7474/browser/)
  * Connect to the API docker container
  * Run a workflow via the API. 
  ```
  $ cd ../ros
  $ PYTHONPATH=$PWD/.. python app.py --api --workflow workflows/workflow_one.ros -l workflows -i disease_name="type 2 diabetes mellitus" --out stdout
  ```
### Usage - Programmatic

Ros can execute workflows remotely and return the resulting knowledge network. The client currently supports JSON and NetowrkX representations.

  ```
  from ros.client import Client
 
  ros = Client (url="http://localhost:5002")
  response = ros.run (workflow='workflows/workflow_one.ros',
                      args = { "disease_name" : "type 2 diabetes mellitus" },
                      library_path = [ 'workflows' ])

  graph = response.to_nx ()    
  for n in graph.nodes (data=True):
      print (n)
  ```

### Install

**Requirements:**

  * Python >3.7.x
  * Neo4J >3.3.4
  
**Steps:**

These steps install the package, print help text, and execute  workflow one. To run this, you'll need workflow_one.ros and bionames.ros from the repo. The `-l workflows` flag names the directory containing the workflows.

```
$ pip install ros
$ ros --help
$ ros --workflow workflow_one.ros --arg disease_name="diabetes mellitus type 2" -l workflows
```

### NDEx

To save a workflow to NDEx.

  * Create an NDEx account.
  * Create an ~/.ndex credential file like this:

    ```
    {
      "username" : "<username>",
      "password" : "<password>"
    }
    ```
  * Run the workflow with NDEx output:

    ```
    ros flow --workflow workflow_one.ros --out output.json --ndex wf1
    ```

### Help


  ```
  $ PYTHONPATH=$PWD/.. python app.py --help
  usage: app.py [-h] [-a] [-w WORKFLOW] [-s SERVER] [-i ARG] [-o OUT]
                [-l LIBPATH] [-n NDEX] [--validate]

  Ros Workflow CLI

  optional arguments:
    -h, --help                        show this help message and exit
    -a, --api                         URL of the remote Ros server to use.
                                      (default: False)
    -w WORKFLOW, --workflow WORKFLOW  Workflow to execute. (default:
                                      workflow_one.ros)
    -s SERVER, --server SERVER        Hostname of api server (default:
                                      http://localhost:5002)
    -i ARG, --arg ARG                 Add an argument expressed as key=val
                                      (default: [])
    -o OUT, --out OUT                 Output the workflow result graph to a
                                      file. Use 'stdout' to print to terminal.
                                      (default: None)
    -l LIBPATH, --libpath LIBPATH     A directory containing workflow modules.
                                      (default: ['.'])
    -n NDEX, --ndex NDEX              Name of the graph to publish to NDEx.
                                      Requires valid ~/.ndex credential file.
                                      (default: None)
    --validate                        Validate inputs and outputs (default:
                                      False)
  ```
  
## Next

* **Information Architecture**: Develop:
  * **Controlled vocabulary**: Especially regarding what the modules are and how they relate
  * **Input and Output Signatures**: For the modules
  * **Provenance**: Both in terms of workflow provenance (which user, how long, etc) and metadata about sources (SCEPIO?).
* **Polymorphism**: It would be really helpful if multiple entities implementing a capability could implement the same OpenAPI interface to enable polymorphic invocation. This would also help with parallelism.
* **[KGX](https://github.com/NCATS-Tangerine/kgx)**: Maybe KGX should be the shared graph, at least optionally. Just need to design that connection.
* **Concurrent / Parallel / Distributed**: Ros now supports concurrent task execution via Python async. If this turns out not to be enough, explore running via something capable of parallel and maybe distributed execution.
* **Composability**: Allow workflows to import and reuse other workflows.

