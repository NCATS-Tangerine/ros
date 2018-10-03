# Ros Global.
export APP_NAME=ros
export PYTHONPATH=$APP_ROOT

# Ros API.
export ROS_WF_PORT=5008

# AMQP server.
export RABBITMQ_DEFAULT_VHOST=$APP_NAME
export RABBITMQ_DEFAULT_USER=guest
export RABBITMQ_DEFAULT_PASS=guest
#export ADMIN_PASSWORD=admin
export BROKER_AUTH="$RABBITMQ_DEFAULT_USER:$RABBITMQ_DEFAULT_PASS@"
export BROKER_HOST=${BROKER_HOST:-amqp}
export BROKER_PORT=${BROKER_PORT:-5672} #12333
export BROKER_ADMIN_PORT=12334

# Celery Task Queue - AMQP and Redis result store config.
export RESULTS_HOST=${RESULTS_HOST:-redis}
export RESULTS_PORT=6345
export RESULTS_DB=0
export CELERY_BROKER_URL="amqp://$RABBITMQ_DEFAULT_USER:$RABBITMQ_DEFAULT_PASS@$BROKER_HOST:$BROKER_PORT/$RABBITMQ_DEFAULT_VHOST"
export CELERY_RESULT_BACKEND="redis://$RESULTS_HOST:$RESULTS_PORT/$RESULTS_DB"
export CELERY_APP_PACKAGE="ros.dag"

# Gamma config.
export GAMMA_HOST=${BUILDER_HOST:-robokop.renci.org}
export BUILDER_PORT=6010
export RANKER_PORT=6011
export BUILDER_BUILD_GRAPH_ENDPOINT=api/
export BUILDER_TASK_STATUS_ENDPOINT=api/task/
export ROBOKOP_BUILDER_BUILD_GRAPH_URL="http://$GAMMA_HOST:$BUILDER_PORT/${BUILDER_BUILD_GRAPH_ENDPOINT}"
export ROBOKOP_BUILDER_TASK_STATUS_URL="http://$GAMMA_HOST:$BUILDER_PORT/${BUILDER_TASK_STATUS_ENDPOINT}"
export ROBOKOP_RANKER_RESULT_URL="http://$GAMMA_HOST:$RANKER_PORT/api/result"
export ROBOKOP_RANKER_NOW_URL="http://$GAMMA_HOST:$RANKER_PORT/api/now?max_results=250"
