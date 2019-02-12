import json
import pytest
from ros.tranql import TranQL

def test_set ():
    tranql = TranQL ()
    tranql.execute ("""
        -- Test set statements.
        
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/' """)

    variables = [ "disease", "max_p_value", "cohort", "icees.population_density_cluster", "gamma.quick" ]
    output = { k : tranql.context.resolve_arg (f"${k}") for k in variables }
    print (f"--> {json.dumps(output, indent=2)}")
    assert output['disease'] == "'asthma'"
    assert output['cohort'] == "'COHORT:22'"
    

def test_tranql ():
    tranql = TranQL ()
    tranql.execute ("""
        -- Workflow 5
        --   Modules 1-4: Chemical Exposures by Clinical Clusters
        --      For sub-clusters within the overall ICEES asthma cohort defined by
        --      differential population density, which chemicals are related to these clusters
        --      with a p_value less than some threshold?
        --   Modules 5-*: Knowledge Graph Phenotypic Associations 
        --      For chemicals produced by the first steps, what phenotypes are associated with exposure
        --      to these chemicals?
        
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/'

        SELECT disease->chemical_substance
          FROM $icees.population_density_cluster
         WHERE disease = $disease
           AND population_density < $population_density
           AND cohort = $cohort
           AND max_p_value = $max_p_value
           SET '$.nodes.[*]' AS exposures

        SELECT chemical_substance->gene->biological_process->phenotypic_feature
          FROM $gamma.quick
         WHERE chemical_substance = $exposures
           SET knowledge_graph """)
    expos = tranql.context.resolve_arg("$exposures")
    print (f" {json.dumps(expos)}")

