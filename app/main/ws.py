import json
import logging

import datadog
from flask import current_app, request
from flask_sock import Sock
from kubernetes import client, watch
from kubernetes.client.rest import ApiException

from .. import default

sock = Sock()


@sock.route("/ws/logstream")
@datadog.statsd.timed(metric="dinghy_ping_events_web_socket_duration.timer")
def log_stream_websocket(ws):
    k8s_client = client.CoreV1Api()

    name = request.args["name"]
    namespace = request.args["namespace"]
    container = request.args["container"]

    try:
        resp = k8s_client.read_namespaced_pod_log(
            name,
            namespace,
            container=container,
            tail_lines=current_app.config["TAIL_LINES_DEFAULT"],
            follow=True,
            _preload_content=False,
        )
    except ApiException as e:
        if e.status == 404:
            ws.send("Pod not found")
            ws.close()

    while True:
        try:
            line = resp.readline()
        except Exception as e:
            logging.error(
                f"""
                issue reading pod logs: {e}
            """
            )
            break
        if not line:
            break
        ws.send(line.decode("utf-8"))

    ws.close()


@sock.route("/ws/event-stream")
@datadog.statsd.timed(metric="dinghy_ping_events_web_socket_duration.timer")
def event_stream_websocket(ws):
    namespace = request.args["namespace"]
    filter = request.args["filter"]

    if filter == "all":
        field_selector = ""
    elif filter == "pod":
        field_selector = "involvedObject.kind=Pod"
    else:
        logging.info("event-stream filter is defaulting to all events")
        field_selector = ""

    v1 = client.CoreV1Api()
    w = watch.Watch()

    for event in w.stream(
        v1.list_namespaced_event, namespace, field_selector=field_selector
    ):
        obj = event["object"]
        event_resp = dict(Name=obj.metadata.name, Message=obj.message)

        event_resp_json_dump = json.dumps(event_resp, default=default)
        ws.send(event_resp_json_dump)

    ws.close()
