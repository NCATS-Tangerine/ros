#!/bin/bash

if [[ "$UPDATE_REPO" -eq "yes" ]]; then
    test -d ros && (cd ros; git pull) || echo yes | git clone "https://github.com/NCATS-Tangerine/ros-t10r.git"
    test -d ros && (cd ros; git pull) || echo yes | git clone "https://github.com/NCATS-Tangerine/ros"
fi

ROOT=/
ROS_HOME=$ROOT/ros
ROS_T10R_HOME=$ROOT/ros-t10r

pip install -r $ROS_HOME/ros/requirements.txt
#pip install -r $ROS_T10R_HOME/requirements.txt

cd $ROS_HOME/ros

export PYTHONPATH=$ROS_HOME:$ROS_T10R_HOME

# $PWD/..:$PWD/../../ros-t10r/ \
# PYTHONPATH=$PYTHONPATH \

gunicorn ros.api.api:app \
         --bind 0.0.0.0:$API_PORT \
         --worker-class sanic.worker.GunicornWorker
