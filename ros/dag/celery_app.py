from __future__ import absolute_import, unicode_literals
from __future__ import absolute_import
from celery import Celery
from kombu import Queue
import ros.dag.conf as Conf

app = Celery(Conf.celery_app_package)
app.conf.update(
    broker_url=Conf.celery_broker_url,
    result_backend=Conf.celery_result_backend,
    include=[ f'{Conf.celery_app_package}.tasks' ]
)
app.conf.task_queues = (
    Queue('rosetta', routing_key='rosetta'),
)
