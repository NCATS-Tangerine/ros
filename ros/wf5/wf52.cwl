cwlVersion: v1.0
class: Workflow
inputs:
  icees_endpoint: string
  icees_question: File
  icees_response: string
  gamma_endpoint: string
  gamma_question: File
  gamma_select: string
  gamma_filter_val: string
  gamma_response: string
outputs:
  knowledge_graph:
    type: File
    outputSource: gamma/kg_out
steps:
  icees:
    run: roscwlapi.cwl
    in:
      service: icees_endpoint
      question: icees_question
      output: icees_response
    out: [kg_out]
  gamma:
    run: roscwlapi.cwl
    in:
      service: gamma_endpoint
      question: gamma_question
      source: icees/kg_out
      select: gamma_select
      type: gamma_filter_val
      output: gamma_response
    out: [kg_out]
