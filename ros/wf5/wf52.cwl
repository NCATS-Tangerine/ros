cwlVersion: v1.0
class: Workflow
inputs:
  inp_disease: string
  inp_kg_path: File
  out_kg_path: string

outputs:
  knowledge_graph:
    type: File
    outputSource: untar/kg_out

steps:
  untar:
    run: roscwlapi.cwl
    in:
      inp_disease: inp_disease
      input: inp_kg_path
      output: out_kg_path
    out: [kg_out]

#  compile:
#    run: arguments.cwl
#    in:
#      src: untar/example_out
#    out: [classfile]
