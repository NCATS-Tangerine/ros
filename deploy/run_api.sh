#!/bin/bash

####################################################################
#
#  Runs the Translator Ros workflow web service.
#    - Clone and optionally update 

ROOT=/

if [[ "$UPDATE_REPO" -eq "yes" ]]; then
    cd $ROOT
    test -d ros-t10r && (cd ros-t10r; test "$UPDATE_REPO" == true && git pull) || echo yes | git clone "https://github.com/NCATS-Tangerine/ros-t10r.git"
    cd $ROOT
    test -d ros && (cd ros; test "$UPDATE_REPO" == true && git pull) || echo yes | git clone "https://github.com/NCATS-Tangerine/ros"
fi

ROS_HOME=$ROOT/ros
ROS_T10R_HOME=$ROOT/ros-t10r

pip install -r $ROS_HOME/ros/requirements.txt

cd $ROS_HOME/ros

export PYTHONPATH=$ROS_HOME:$ROS_T10R_HOME

gunicorn ros.api.api:app \
         --bind 0.0.0.0:$API_PORT \
         --timeout 60000 \
         --worker-class sanic.worker.GunicornWorker
