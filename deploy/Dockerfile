FROM python:3.6.5

RUN git clone "https://github.com/NCATS-Tangerine/ros" "ros" 2> /dev/null || (cd "ros" ; git pull)

WORKDIR /ros/ros

RUN pip install -r requirements.txt

ENV ROS_HOME /ros
ENV ROS_PORT 5002
ENV LOG_FILE /var/log/ros/ros.log

RUN useradd -m -s /bin/bash ros

RUN apt update
RUN apt-get install -y emacs24-nox

ENV PYTHONPATH /ros

ENTRYPOINT python api/api.py --port $ROS_PORT

#ENTRYPOINT gunicorn \
#                    --timeout 3000 \
#                    --bind 0.0.0.0:$ROS_PORT \
#                    --pythonpath $ROS_HOME \
#                    --error-logfile $LOG_FILE \
#                    --log-file $LOG_FILE \
#                    --log-level debug \
#                    --capture-output \
#                    ros.api.api:app

