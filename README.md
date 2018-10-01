# Ros

## Workflows

The Ros workflow engine and API execute graphs of queries to compose knowledge networks answering biomedical questions.

The language provides familiar constructs like variables, modularity, extensibility, templates, a type system, and dependency management. At the same time, it is responsive to the distinctive needs of the Biomedical Translator which seeks to create highly detailed knowledge graps enabling sophisticated biomedical reasoning.

## Language

A workflow is a series of steps.
Each step can reference a predefined operation via the `code` tag.
These operations accept a set of arguments specified via the args tag.
When an operation executes, its result is implicitly stored and can be addressed later by the operator's name.

## Variables

Variables passed to the workflow can be resolved dynamically. In this example, $disease_name refers to an argument provided by the execution context to this workflow. The provided value will be substituted at runtime.

```
  diseases:
    doc: |
      Analogous English to ontological identifier transformation for disease.
    code: name2id
    args:
      type: disease
      input: $disease_name
```

## Graphs

Ros provides graphs in two basic modalities:

* **Results**: Results of previous workflow steps can be referenced as variables passed to subsequent steps. This graph can be queried using JSON Path query syntax.
* **Shared**: A shared graph, accessible with the Cypher query language is available to all operators.

Each operator receives an event object provided by the Ros framework. The event provides framework services including the shared graph, graph manipulation tools, and arguments to the invocation of the operator.

These facilities allow the operator to query the graphs before executing their main logic and to update it as well.

## Operators

The system provides the following core operators.

If the community is able to develop common APIs to reasoners, this profile will shift to supporting those common APIs.

* **bionames** Invokes the Bionames API to resolve a natural language string to ontology identifiers.
* **gamma** Invokes the Gamma reasoner. The example below calls Gamma a few times with different machine questions. It will be updated to use the new Quick API for added flexibility.
* **biothings** BioThings modules.
* **get** Invokes an HTTP GET operation on a specified resource.
* **union** Unions two or more results into one object.
* **xray** XRay reasoner modules.

## Metadata

The language supports a metadata capability to enable modules to specify their inputs and outputs.

Inputs and outputs can be specified with annotations specifying

* **Type**: Types are currently derived from a standard library but in the future will be extensible and composable.
* **Required**: Whether or not the argument is required.

The use of metadata is optional.

## Templates

Templates allow the extension and specialization of existing library functions into new capabilities through composition.

It's possible to speicify a template that pre-populates arguments of an operation and to register that template as an operator. It can then be invoked by a workflow which includes it.

## Modules

External modules can be loaded via the `import` tag.

A library path like those featured in other high level programming languages governs where libraries are loaded from.

## Putting it All Together

Let's take a closer look at a usage example that puts this all together.

Below, is a template called bionames.

* It is built on the builtin `get` operator and sets the `pattern` argument to a defined value.
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

It further populates the type and input arguments required by the template.

Executing this module will produce a JSON object that can be referenced elsewhere in the workflow as `$disease_identifiers`.

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
