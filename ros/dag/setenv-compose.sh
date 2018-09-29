#!/bin/bash

# Environment dependent settings:

export APP_ROOT=${APP_ROOT:-~/dev/reasoner-tools}
export APP_PORT=5006
export NUM_WORKERS=3
export BROKER_HOST=redis
export RESULTS_HOST=amqp
