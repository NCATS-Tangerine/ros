from __future__ import absolute_import, unicode_literals
from __future__ import absolute_import
from celery import Celery
from kombu import Queue
from ros.config import Config
import json

config = Config ("ros.yaml")
app = Celery(config["celery_app_package"])
app.conf.update(
    broker_url=config['celery_broker_url'],
    result_backend=config['celery_result_backend'],
    include=[ f"{config['celery_app_package']}.tasks" ]
)
app.conf.task_queues = (
    Queue('rosetta', routing_key='rosetta'),
)
