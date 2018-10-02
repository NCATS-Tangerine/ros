# Ros

## Workflows

The Ros workflow engine executes query graphs to compose knowledge networks.

While the language provides common programming language constructs including variables, modularity, extensibility, templates, a type system, and dependency management, it is targeted at the distinctive challenges of creating **highly detailed knowledge graps enabling sophisticated reasoning and inference**. The model supposes that this knowledge network construction will occur in the context of federated knowledge sources (like web APIs) supplying components of resulting graphs.

## Language

### Very High Level Overview
A workflow is a series of steps.
Each step can reference an executable component via the `code` tag.
These workflow steps accept a set of arguments specified via the `args` tag.
These executable components can, in some cases, be further qualified via the `op` tag to specify a more granular component.
When an operation executes, its result is implicitly stored and can be addressed later by the operator's name.

## Variables

Variables passed to the workflow at the command line or via the API can be resolved dynamically. In this example, $disease_name refers to an argument provided by the execution context to this workflow. The provided value will be substituted at runtime.

```
  diseases:
    doc: |
      Analogous English to ontological identifier transformation for disease.
    code: name2id
    args:
      type: disease
      input: $disease_name
```

## Operators

The workflow is organized around graph operator components.

Each one has access to a shared graph and other facilities of the Ros framework.

In general, each element of a workflow has the following standard contents:

  * **doc**: A documentation string.
  * **code**: The name of a component providing functionality.
  * **args**: Arguments to the operator.

The system provides the following core operators.

If the community is able to develop common APIs to reasoners, this profile will shift to supporting those common APIs.

* **bionames**: Invokes the Bionames API to resolve a natural language string to ontology identifiers.
* **gamma**: Invokes the Gamma reasoner. The example below calls Gamma a few times with different machine questions. It will be updated to use the new Quick API for added flexibility.
* **biothings**: BioThings modules.
* **get**: Invokes an HTTP GET operation on a specified resource.
* **union**: Unions two or more results into one object.
* **xray**: XRay reasoner modules.

## Graphs

Ros provides graphs in two basic modalities:

* **Results**: Results of previous workflow steps can be referenced as variables passed to subsequent steps. This graph can be queried using JSON Path query syntax.
* **Shared**: A shared graph, accessible with the Cypher query language is available to all operators.

Each operator receives an event object provided by the Ros framework. The event provides framework services including the shared graph, graph manipulation tools, and arguments to the invocation of the operator.

These facilities allow the operator to query the graphs before executing their main logic and to update it as well.

## Metadata

The language supports a metadata capability to enable modules to specify their inputs and outputs.

Inputs support these tags:

* **doc**: Documentation
* **type**: Types are currently derived from a standard library but in the future will be extensible and composable.
* **required**: Whether or not the argument is required.

Outputs support these tags:
* **doc**: Documentation.
* **type**: Type of the returned object.

The use of metadata is optional.

## Templates

Templates allow extension of the language by specializing existing library functions into new capabilities through composition. Templates are defined in a template section separate from the workflow proper. They can also be defined in separate, reusable modules.

## Modules

External modules can be loaded via the `import` tag.

A library path like those featured in other high level programming languages governs where libraries are loaded from.

## Putting it All Together

Here's a usage example to put all of this in context.

To begin with, here is a template called bionames.

* It extends the builtin `get` operator and sets the `pattern` argument to a defined value.
* It's saved to a file called `bionames.ros` in a directory that's on the library path.
* The `meta` tag describes metadata about the operator.
* The special `main` operator is used when no sub-operators are specified.
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

Next, we import the templat above into a workflow definition.

```
doc: |
  NCATS Biomedical Translator - Workflow One
  
import:
  - bionames
  
workflow:

  disease_identifiers:
    doc: |
      Resolve an English disease name to an ontology identifier.
    code: bionames
    args:
      type: disease
      input: $disease_name
...
```

Within the workflow section, the first operator names the imported bionames template as the job to execute.

It also populates the type and input arguments required by the template.

Executing this module will produce a JSON object that can be referenced elsewhere in the workflow as `$disease_identifiers`.

The next step in the workflow executes the first modules of workflow one via the XRay reasoner:

```
  condition_to_drug:
    doc: |
      Module 1
        * What are the defining symptoms / phenotypes of [condition x]?
        * What conditions present [symptoms]?
        * Filter [conditions] to only keep ones with defined genetic causes.
        * What subset of conditions are most representative of [conditions]? (find archetypes)
      Module 2
        * What genes are implicated in [condition]?
        * What subset of genes are most representative of [conditions]?  (find archetypes)
        * What pathways/processes are [genes] involved in?
        * What genes are involved in [pathway/process]?
        * What drugs/compounds target gene products of [gene]?
      Invoke XRay module 1 and 2 given the disease identifier from bionames.
      The graph argument references the entire bionames response.
      The op argument specifies the XRay operation to execute.
    code: xray
    args:
      op: condition_expansion_to_gene_pathway_drug
      graph: $disease_identifiers
```

The graph argument references the output from our bionames command above as an input via a variable.

For more details, see the whole [workflow](https://github.com/NCATS-Tangerine/ros/blob/sharedgraph/ros/workflow_one.ros).

## Output

Here's some output from running the workflow above with validation enabled. It shows importing the bionames module, validating each invocation (only disease_identfiers has metadata configured).

It then builds the dependency graph.

```
$ ros flow --workflow workflow_one.ros --validate
importing
  module: bionames from ./bionames.ros
validating
  validate(disease_identifiers).
  validate(condition_to_drug).
  validate(module_3).
  validate(biothings_module_4_and_5).
  validate(return).
Validation successful.
dependencies
  xray->disease_identifiers
  gamma->disease_identifiers
  biothings->condition_to_drug
  union->biothings_module_4_and_5
```

## Execution

For all workflows, the engine builds a directed acyclic graph (DAG) of jobs by examining each job to determine its dependencies.

A topological sort of the jobs provides the execution order.

There are two basic execution modes.

* **Synchronous** The prototype runs jobs synchronously.
* **Asynchronous** Under development is a task queue based approach.
  Each job is sent, via an AMQP message queue to an execution back end (Celery).
  Job results are stored in Redis.
  Ultimately, other back ends would be good.

## Usage

Clone the repo

```
git clone git@github.com:NCATS-Tangerine/ros.git
cd ros
```

Add ros to the path.
```
export PATH=$PWD/bin:$PATH
```

Change to the workflow directory.
```
cd ros
```

Install requirements:
```
pip install -r requirements.txt
```

Run the workflow.
```
ros flow --workflow workflow_one.ros --out output.json
```

Save a workflow to NDEx:

Create an NDEx account.

Create an ~/.ndex credential file like this:

```
{
  "username" : "<username>",
  "password" : "<password>"
}
```

Run the workflow with NDEx output:

```
ros flow --workflow workflow_one.ros --out output.json --ndex_id wf1
```

Help:
```
$ ros flow --help
usage: run_tasks.py [-h] [-a] [-w WORKFLOW] [-s SERVER] [-p PORT] [-i ARG]
                    [-o OUT] [-l LIB_PATH] [-n NDEX_ID] [--validate]

Rosetta Workflow CLI

optional arguments:
  -h, --help                        show this help message and exit
  -a, --api                         Execute via API instead of locally.
  -w WORKFLOW, --workflow WORKFLOW  Workflow to execute.
  -s SERVER, --server SERVER        Hostname of api server
  -p PORT, --port PORT              Port of the server
  -i ARG, --arg ARG                 Add an argument expressed as key=val
  -o OUT, --out OUT                 Output the workflow result graph to a
                                    file. Use 'stdout' to print to terminal.
  -l LIB_PATH, --lib_path LIB_PATH  A directory containing workflow modules.
  -n NDEX_ID, --ndex_id NDEX_ID     Publish the graph to NDEx
  --validate                        Validate inputs and outputs
  ```
  
## Next

We've barely begun.

* **Parallel / Distributed**: Execute via something capable of parallel, distributed execution. Current likely options include Celery and Kubernetes.
* **Composability**: Allow workflows to import and reuse other workflows.
