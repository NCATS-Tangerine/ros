import os

app_name = os.environ["APP_NAME"]
celery_app_package = os.environ["CELERY_APP_PACKAGE"]
celery_broker_url = os.environ["CELERY_BROKER_URL"]
celery_result_backend = os.environ["CELERY_RESULT_BACKEND"]

results_host = os.environ["RESULTS_HOST"]
results_port = os.environ["RESULTS_PORT"]

robokop_builder_build_url = os.environ["ROBOKOP_BUILDER_BUILD_GRAPH_URL"]
robokop_builder_task_status_url = os.environ["ROBOKOP_BUILDER_TASK_STATUS_URL"]

robokop_ranker_result_url = os.environ["ROBOKOP_RANKER_RESULT_URL"]
robokop_ranker_now_url = os.environ["ROBOKOP_RANKER_NOW_URL"]
