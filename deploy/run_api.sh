#!/bin/bash

test -d ros && (cd ros; git pull) || echo yes | git clone "https://github.com/NCATS-Tangerine/ros"

ROS_HOME=/ros
cd $ROS_HOME/ros

PYTHONPATH=$ROS_HOME

#python api/api.py --port $ROS_PORT

PYTHONPATH=$PWD/.. gunicorn ros.api.api:app --bind 0.0.0.0:5002 --worker-class sanic.worker.GunicornWorker 
