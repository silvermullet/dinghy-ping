import subprocess
import logging
from celery import Celery
from flask import current_app

class GrpCurl:
    def __init__(self, grpc_url, grpc_port, json):
        self.grpc_url = grpc_url
        self.grpc_port = grpc_port

    celery = Celery(__name__)
    celery.conf.broker_url = current_app.config["CELERY_BROKER_URL"]
    celery.conf.result_backend = current_app.config["CELERY_RESULT_BACKEND"]

    # run subprocess to /root/bin/grpcurl to grpc server url and port
    def run(self, method, data):
        cmd = f"/root/bin/grpcurl -plaintext {self.grpc_url}:{self.grpc_port} {method} {data}"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8')

    @celery.task(name="grpcurl_tasks") 
    def run_batch(self, method, json_input):
        for obj in json_input:
            cmd = f"/root/bin/grpcurl -plaintext {self.grpc_url}:{self.grpc_port} {method} {obj}"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout.decode('utf-8')