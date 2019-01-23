#!/usr/bin/env cwl-runner
# This tool description was generated automatically by argparse2tool ver. 0.4.5
# To generate again: $ cwlapi.py -go --generate_cwl_tool
# Help: $ cwlapi.py  --help_arg2cwl

cwlVersion: v1.0

class: CommandLineTool
baseCommand: ['cwlapi.py']

doc: |
  Ros CWL API

inputs:
  
  drug:
    type: boolean
    default: False
    doc: URL of the remote Ros server to use.
    inputBinding:
      prefix: --drug 


outputs:
    []
