#!/bin/bash

# Environment dependent settings:

script_bin=$(dirname ${BASH_SOURCE[0]})

export APP_ROOT=~/dev/reasoner-tools
export APP_PORT=5006
export NUM_WORKERS=3
export BROKER_HOST=localhost
export RESULTS_HOST=localhost
export BROKER_PORT=56722

source ${script_bin}/conf.sh

