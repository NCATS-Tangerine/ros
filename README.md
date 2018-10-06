
<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/ros.png" width="40%"></src>

The Ros engine executes query graphs to compose knowledge networks.

While the language provides common constructs supporting variables, modularity, extensibility, templates, and a type system, it is targeted at the distinctive challenges of creating **highly detailed knowledge graphs enabling reasoning and inference**.

## Language

### Overview

A workflow is a series of steps.
Steps can reference the output of previous steps.
In general they have access to a shared graph.
They can also exchange sub-graphs.
Steps can have associated metadata describing their allowed input and output types.

Workflows compute a directed acyclic graph (DAG) modeling job dependencies which are then executed in the order indicated by a topological sort of the DAG.

### Variables

Variables passed to the workflow at the command line or via the API can be resolved dynamically. In this example, $disease_name refers to an argument provided by the execution context to this workflow. The provided value will be substituted at runtime. The name `disease_identifiers` is the job's name. When it completes, the knowledg graph standard graph it produces will be saved as the value of the job's name. The graph is also written to the shared graph.

The `code` tag tells the engine which block of functionality to execute.

The `args` section lists inputs to this operator.

```
  disease_identifiers:
    doc: |
      Resolve an English disease name to an ontology identifier.
    code: bionames
    args:
      type: disease
      input: $disease_name
```

### Operators

The workflow is organized around graph operators. Each has access to all facilities of the Ros framework including the shared graph.

In general, workflow jobs have the following fields:

  * **doc**: A documentation string.
  * **code**: The name of a component providing functionality.
  * **args**: Arguments to the operator.

Ros currently provides the following core operators:

* **get**: Invokes an HTTP GET operation on a specified resource.
* **union**: Unions two or more results into one object.

It also includes certain Translator specific modules. In the future, these will be implemented as Ros plugin: 
* **biothings**: BioThings modules. Currently modules 4 and 5 of workflow 1.
* **gamma**: Invokes the Gamma reasoner. The example below calls Gamma a few times with different machine questions. It will be updated to use the new Quick API for added flexibility.
* **xray**: XRay reasoner modules. Currently modules 1 and 2 of workflow 1.

### Graphs

Ros provides graphs in two basic modalities:

* **Results**: Results of previous workflow steps can be referenced as variables passed to subsequent steps. This graph can be queried using JSON Path query syntax.
* **Shared**: A shared graph, accessible with the Cypher query language is available to all operators.

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

## Putting it All Together

Here's a usage example to put all of this in context.

To begin with, here is a template called bionames.

* It extends the builtin `get` operator and sets the `pattern` argument to a defined value.
* It's saved to a file called `bionames.ros` in a directory that's on the library path.
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

Next, we import the template above into a workflow definition.

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

For more details, see the whole [workflow](https://github.com/NCATS-Tangerine/ros/blob/master/ros/workflow_one.ros).

## Output

Here's output from a recent run of workflow_one.ros with validation enabled.

It shows importing the bionames module, validating each invocation (only disease_identfiers has metadata configured).

It then builds the dependency graph.

Next, it executes jobs in dependency order.

<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/run.png" width="340%"></src>

Here's a portion of the knowledge graph created by executing the workflow:

<img src="https://github.com/NCATS-Tangerine/ros/blob/master/media/wf1_output.png" width="40%"></src>

## Execution

For all workflows, the engine builds a directed acyclic graph (DAG) of jobs by examining each job to determine its dependencies.

A topological sort of the jobs provides the execution order.

There are two basic execution modes.

* **Synchronous** The prototype runs jobs synchronously.
* **Asynchronous** Under development is a task queue based approach.
  Each job is sent, via an AMQP message queue to an execution back end (Celery).
  Job results are stored in Redis.
  Ultimately, other back ends would be good.

## Getting Started

### Install

These steps install the package, print help text, and execute  workflow one. To run this, you'll need workflow_one.ros and bionames.ros from the repo.

```
$ pip install ros
$ ros --help
$ ros --workflow workflow_one.ros --arg disease_name="diabetes mellitus type 2"
```

**Note**: Currently, the Python ndex2 client depends on an old version of NetworkX that's incompatible with Ros. A new version is expected soon. They can be used together but the install process is a bit more complicated than above.

### NDEx

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

Ros Workflow CLI

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

* **Information Architecture**: Develop:
  * **Controlled vocabulary**: Especially regarding what the modules are and how they relate
  * **Input and Output Signatures**: For the modules
  * **Provenance**: Both in terms of workflow provenance (which user, how long, etc) and metadata about sources (SCEPIO?).
* **Polymorphism**: It would be really helpful if multiple entities implementing a capability could implement the same OpenAPI interface to enable polymorphic invocation. This would also help with parallelism.
* **[KGX](https://github.com/NCATS-Tangerine/kgx)**: Maybe KGX should be the shared graph, at least optionally. Just need to design that connection.
* **Parallel / Distributed**: Execute via something capable of parallel, distributed execution. Current likely options include Celery and Kubernetes.
* **Composability**: Allow workflows to import and reuse other workflows.

