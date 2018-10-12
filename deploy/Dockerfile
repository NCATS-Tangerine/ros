FROM python:3.7

RUN git clone "https://github.com/NCATS-Tangerine/ros" "ros" 2> /dev/null || (cd "ros" ; echo yes | git pull)

WORKDIR /ros

RUN pip install -r ros/requirements.txt

ENV ROS_HOME /ros
ENV ROS_PORT 5002
ENV LOG_FILE /var/log/ros/ros.log

RUN useradd -m -s /bin/bash ros

RUN apt update
RUN apt-get install -y emacs24-nox

ENV PYTHONPATH /ros

ADD ./run_api.sh /ros/run_api.sh
RUN chmod +x /ros/run_api.sh

ENTRYPOINT /ros/run_api.sh





#ENTRYPOINT python api/api.py --port $ROS_PORT

#ENTRYPOINT gunicorn \
#                    --timeout 3000 \
#                    --bind 0.0.0.0:$ROS_PORT \
#                    --pythonpath $ROS_HOME \
#                    --error-logfile $LOG_FILE \
#                    --log-file $LOG_FILE \
#                    --log-level debug \
#                    --capture-output \
#                    ros.api.api:app

# PYTHONPATH=$PWD/.. gunicorn ros.api.api:app --bind 0.0.0.0:5002 --worker-class sanic.worker.GunicornWorker 

