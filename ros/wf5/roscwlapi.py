#!/usr/bin/env python

import argparse

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description='Ros CWL API',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=60))
    arg_parser.add_argument('--drug', help="URL of the remote Ros server to use.", default="asthma")
    arg_parser.add_argument('--kg', help="knowledge_graph", type=argparse.FileType('w'))
    
    args = arg_parser.parse_args ()

    with open('kg_out', 'w') as stream:
        stream.write ("{}")
        
