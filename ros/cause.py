
import pandas as pd
import numpy as np
from causality.inference.search import IC
from causality.inference.independence_tests import RobustRegressionTest

SIZE = 2000
x1 = np.random.normal(size=SIZE)
x2 = x1 + np.random.normal(size=SIZE)
x3 = x1 + np.random.normal(size=SIZE)
x4 = x2 + x3 + np.random.normal(size=SIZE)
x5 = x4 + np.random.normal(size=SIZE)

# load the data into a dataframe:
X = pd.DataFrame({'x1' : x1, 'x2' : x2, 'x3' : x3, 'x4' : x4, 'x5' : x5})

# define the variable types: 'c' is 'continuous'.  The variables defined here
# are the ones the search is performed over  -- NOT all the variables defined
# in the data frame.
variable_types = {'x1' : 'c', 'x2' : 'c', 'x3' : 'c', 'x4' : 'c', 'x5' : 'c'}


ic_algorithm = IC(RobustRegressionTest)
graph = ic_algorithm.search(X, variable_types)

e = graph.edges(data=True)
print (f"{e}")

SIZE = 2000
x1 = np.random.normal(size=SIZE)
x2 = x1 + np.random.normal(size=SIZE)
x3 = x1 + np.random.normal(size=SIZE)
x6 = np.random.normal(size=SIZE)
x4 = x2 + x3 + x6 + np.random.normal(size=SIZE)
x5 = x6 + np.random.normal(size=SIZE)

# load the data into a dataframe:
X = pd.DataFrame({'x1' : x1, 'x2' : x2, 'x3' : x3, 'x4' : x4, 'x5' : x5})

# define the variable types: 'c' is 'continuous'.  The variables defined here
# are the ones the search is performed over  -- NOT all the variables defined
# in the data frame.
variable_types = {'x1' : 'c', 'x2' : 'c', 'x3' : 'c', 'x4' : 'c', 'x5' : 'c'}

# run the search
ic_algorithm = IC(RobustRegressionTest)
graph = ic_algorithm.search(X, variable_types)

e = graph.edges(data=True)

print (f"{e}")
