FROM python:3.6.5

RUN git clone "https://github.com/NCATS-Tangerine/ros" "ros" 2> /dev/null || (cd "ros" ; git pull)

WORKDIR /ros/ros
RUN pip install -r requirements.txt
#ENV export PYTHONPATH=/ros
ENV export ROS_PORT=5002

RUN useradd -m -s /bin/bash ros

ENTRYPOINT gunicorn \
                    --timeout 3000 \
                    --bind 0.0.0.0:$ROS_PORT \
                    --pythonpath /ros \
                    ros.api.api:app

