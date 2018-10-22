import json
import logging
import re
import requests
from ros.framework import Operator
from ros.util import Syfur

logger = logging.getLogger("validate")
logger.setLevel(logging.WARNING)

class Validate (Operator):
    """ Tools for validating a workflow graph. """

    def __init__(self):
        self.syfur = Syfur ()
        
    def invoke (self, event):
        """ Execute validations. """

        result = {}

        """ Test activation condition. """
        var = event.context.resolve_arg (event.when['var'])
        val = event.when['val']
        if not var == val:
            logger.info (f"Skipping validation. Unmet condition: {var} == {val}.")
            return result

        """ Activation condition met. Execute validation. """
        for name, assertion in event.then.items ():
            logger.info (f"Validator running test {name}: {assertion['doc']}")
            items = event.context.graph.query (self.syfur.parse (assertion['items']))

            all_op = assertion.get ("all", None)
            match_op = assertion.get ("match", None)
            none_op = assertion.get ("none", None)

            if all_op:
                for a in all_op:
                    assert a in items, f"Failed to find element {a} in items {items}."
                result['all'] = 'success'
            if match_op:
                for m in match_op:
                    pat = re.compile (m)
                    for i in items:
                        match = pat.match (i)
                        assert match.group (), f"Failed to match element {m} in items {items}."
                result['match'] = 'success'
            if none_op:
                for n in none_op:
                    assert n not in items, f"Found element {n} which must not appear in items {items}."
                result['none'] = 'success'
        return event.context.graph.tools.kgs (nodes=[])
