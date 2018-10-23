FROM python:3.7

RUN git clone "https://github.com/NCATS-Tangerine/ros" "ros" 2> /dev/null || (cd "ros" ; echo yes | git pull)

WORKDIR /ros

RUN pip install -r ros/requirements.txt

ENV UPDATE_REPO yes
ENV ROS_HOME /ros
ENV LOG_FILE /var/log/ros/ros.log
ENV PYTHONPATH /ros
ENV API_TIMEOUT 180
ENV API_PORT 5002

RUN useradd -m -s /bin/bash ros
RUN apt update
RUN apt-get install -y emacs24-nox

ADD ./run_api.sh /ros/run_api.sh
RUN chmod +x /ros/run_api.sh

ENTRYPOINT /ros/run_api.sh


