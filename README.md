# Ros

## Workflows

Workflows are widely used to automate highly complex computing tasks.

The Ros workflow engine and API execute graphs of queries to compose knowledge networks answering biomedical questions.

Ros provide familiar facilities like variables, modularity, extensibility, templates, dependency management, while being responsive to the particular needs of the Translator workflows.

## Language

A workflow is a series of steps.
Each step can reference a predefined operation via the `code` tag.
These operations accept a set of arguments specified via the args tag.
When an operation executes, its result is implicitly stored and can be addressed later by the operator's name.
Variables
Variables passed to the workflow can be resolved dynamically. In this example, $disease_name refers to an argument provided by the execution context to this workflow. The provided value will be substituted at runtime.

  diseases:
    doc: |
      Analogous English to ontological identifier transformation for disease.
    code: name2id
    args:
      type: disease
      input: $disease_name

## Query

An operation may query the output of a previous step.
In this way, a "list" of genes can be created by querying a structure produced elsewhere in the workflow.
The language currently supports a select tag, which, in conjunction with from and where tags is used to target a JSONPath expression at the output of a previous step.
In the example below, the output of the name2id service is indexed by the drug_to_phenotypic_feature operation using a JSONPath expression. That job is an instance of the gamma job for querying the Gamma (Robokop) reasoner.

## Operators

There are currently four built in operators: name2id, gamma, union, and get

    - name2id Invokes the Bionames API to resolve a natural language string to ontology identifiers.
    - gamma Invokes the Gamma reasoner. The example below calls Gamma a few times with different machine questions. It will be updated to use the new Quick API for added flexibility.
    - union Unions two or more results into one object.
    - get Invokes an HTTP GET operation on a specified resource.

We expect to grow this capability in two ways:

Adding Core Operators: By adding intersection and other common graph operations, we can increase the basic capability.
Templates The following section describes how users can compose and extend operations to creat their own.

## Templates

Templates allow the extension and specialization of existing library functions.

templates:
  name2id:
    doc: |
      This is a template. It can be extended by other templates or by operators. 
    code: get
    args:
      pattern: 'https://bionames.renci.org/lookup/{input}/{type}/'
workflow:
  drugs:
    doc: |
      This template accepts a $drug_name variable and specifies the biolink model type for chemical substances.
    extends: name2id
    args:
      inputs:
        - input: $drug_name
          type: chemical_substance
...

## Modules

External modules can be loaded via the import tag.

This module definition,

doc: |
  This module defines a reusable template.
  It can be imported into other workflows via the import directive.

templates:

  name2id:
    doc: |
      This is a template. It can be extended by workflow operators.
      An extending operator will have all attributes of this template. 
    code: get
    args:
      pattern: 'https://bionames.renci.org/lookup/{input}/{type}/'
saved to a file called bionames.ros on the module path, can be loaded from another module like this

import:
  - bionames
and its components referenced by the importing workflow like this:

  drugs:
    doc: |
      This template accepts a $drug_name variable and specifies the biolink model type for chemical substances.
    extends: name2id
    args:
      inputs:
        - input: $drug_name
          type: chemical_substance

## Execution

There are two basic execution modes.

    - **Synchronous** The prototype runs jobs synchronously.
Asynchronous Under development is a task queue based approach.
The engine builds a directed acyclic graph (DAG) of jobs.
A topological sort of the jobs provides the execution order.
Each job is sent, via an AMQP message queue to an execution back end (Celery).
Job results are stored in Redis.
Ultimately, other back ends would be good. Currently investigating FireWorks.
