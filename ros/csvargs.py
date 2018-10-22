import csv
import logging
import json
import traceback

logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

class CSVArgs:
    
    """ Take lists of arguments from a CSV file. """
    
    def __init__(self, csv_file, delimiter='\t'):
        """
        Accept a file path and delimiter.

        Parse the file to an argument list.
        """
        self.vals = []
        with open(csv_file, 'r', encoding='utf-8') as stream:
            print (f"delimiter [{delimiter}]")
            reader = csv.reader (stream, delimiter=delimiter)
            headers = next (reader, None)

            for row in reader:
                values = { a : row[i] for i, a in enumerate(headers) }                
                try:
                    if len(headers) == len(values):
                        self.vals.append (values)
                    else:
                        print (f"detected row with {len(values)} values but only {len(headers)} headers were supplied. skipping.")
                except:
                    traceback.print_exc ()

if __name__ == '__main__':
    c = CSVArgs ('test.csv')
    print (json.dumps (c.vals, indent=2))
