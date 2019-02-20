#!/usr/bin/env cwl-runner

cwlVersion: v1.0

class: CommandLineTool
baseCommand: ['/Users/colincurtis/Documents/renci/ros/ros/wf5/roscwlapi.py']

doc: |
  Ros CWL API

inputs:
  
  service:
    type: string
    doc: HTTP endpoint of the service
    inputBinding:
      prefix: --service
      position: 1
      
  question:
    type: File
    default: ./kg_question
    doc: path to input
    inputBinding:
      prefix: --question
      position: 2
      
  source:
    type: File
    default: null
    doc: path to input from prior step
    inputBinding:
      prefix: --source
      position: 2

  select:
    type: string
    default: null
    doc: jsonpath selector into source object
    inputBinding:
      prefix: --select
      position: 3

  type:
    type: string
    default: null
    doc: biolink-model type to use from previous source.
    inputBinding:
      prefix: --type
      position: 4
      
  output:
    type: string
    default: ./kg_output
    doc: path to output
    inputBinding:
      prefix: --output
      position: 5

outputs:
  kg_out:
    type: File
    doc: output knowledge graph
    outputBinding:
      glob: $(inputs.output)

