#!/bin/bash

####################################################################
#
#  Runs the Translator Ros workflow web service.
#    - Clone and optionally update repos
#    - Configure PYTHONPATH
#    - Install requirements
#    - Start the server
#
####################################################################

ROOT=/

cd $ROOT

manage_repo () {
    local repo=$1
    local url=$2
    echo manage repo $1 url $2 dir $PWD update repo: $UPDATE_REPO
    pop=$PWD
    if [[ -d $repo ]]; then
        if [[ "$UPDATE_REPO" == "yes" ]]; then
            cd $repo
            echo $repo exists and update repo is true. pulling.
            pwd
            git pull
        fi
    else
        echo $repo does not exist. cloning.
        echo yes | git clone $url
    fi
    cd $pop
}

manage_repo ros-translator https://github.com/NCATS-Tangerine/ros-translator.git
manage_repo ros https://github.com/NCATS-Tangerine/ros

ROS_HOME=$ROOT/ros
ROS_TRANSLATOR_HOME=$ROOT/ros-translator
export PYTHONPATH=$ROS_HOME:$ROS_TRANSLATOR_HOME

pip install -r $ROS_HOME/ros/requirements.txt

cd $ROS_HOME/ros

export SANIC_REQUEST_TIMEOUT=$API_TIMEOUT
export SANIC_RESPONSE_TIMEOUT=$API_TIMEOUT

echo $API_TIMEOUT

SCMD="gunicorn ros.api.api:app \
         --bind 0.0.0.0:$API_PORT \
         --timeout $API_TIMEOUT \
         --workers 4 \
         --worker-class sanic.worker.GunicornWorker"

echo $SCMD

$SCMD
