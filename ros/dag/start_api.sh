#!/bin/bash

set -x

export PYTHONPATH=$APP_ROOT
module=greent/flow/dag
source $APP_ROOT/$module/setenv.sh
source $APP_ROOT/$module/conf.sh
python $APP_ROOT/$module/api.py

exit 0
