#!/usr/bin/env cwl-runner
# This tool description was generated automatically by argparse2tool ver. 0.4.5
# To generate again: $ roscwlapi.py -go --generate_cwl_tool
# Help: $ roscwlapi.py  --help_arg2cwl

cwlVersion: v1.0

class: CommandLineTool
baseCommand: ['/Users/scox/dev/ros/ros/roscwlapi.py']

doc: |
  Ros CWL API

inputs:
  
  inp_disease:
    type: ["null", string]
    default: asthma
    doc: URL of the remote Ros server to use.
    inputBinding:
      prefix: --disease

  output:
    type: string
    default: ./kg_output
    doc: path to output
    inputBinding:
      prefix: --output

  input:
    type: File
    default: ./kg_question
    doc: path to input
    inputBinding:
      prefix: --input
      
outputs:
  kg_out:
    type: File
    doc: output knowledge graph
    outputBinding:
      glob: $(inputs.output)

