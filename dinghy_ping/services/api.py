import asyncio
import datetime
import json
import logging
import os
import sys
import traceback
from urllib.parse import urlparse
import datadog
import dns.rdatatype
from ddtrace import patch, tracer
from dinghy_ping.models import dinghy_dns
from dinghy_ping.models.data import DinghyData
from flask import Flask, jsonify, make_response, render_template, request
from flask_sock import Sock
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

patch(requests=True)
import requests  # noqa

logging.basicConfig(level=logging.DEBUG)

TAIL_LINES_DEFAULT = "100"
LOGS_PREVIEW_LENGTH = "1000"
TEMPLATE_DIR = "../views/templates/"
STATIC_DIR = "../views/static/"

environment = os.getenv("ENVIRONMENT", "none")
dd_tags = [f"environment={environment}"]

"""Initialization functions"""


def initialize_datadog():
    dd_statsd_port = os.getenv("DD_DOGSTATSD_PORT", "8125")
    dd_trace_agent_hostname = os.getenv(
        "DD_TRACE_AGENT_HOSTNAME", "host.docker.internal"
    )
    dd_host = os.getenv("DD_AGENT_HOST", "host.docker.internal")
    dd_trace_agent_port = os.getenv("DD_TRACE_AGENT_PORT", "8126")
    datadog_options = {"statsd_host": dd_host, "statsd_port": dd_statsd_port}
    if os.getenv("DD_DOGSTATSD_DISABLE") is None:
        datadog.initialize(
            enabled=False,
            statsd_host="localhost",
            statsd_port=8125,
            statsd_prefix="dinghy_ping",
            statsd_tags=dd_tags,
        )
    else:
        datadog.initialize(**datadog_options)

    if os.getenv("DD_TRACE_ENABLED"):
        tracer.configure(
            hostname=dd_trace_agent_hostname,
            port=dd_trace_agent_port,
            service="dinghy_ping",
            tags=dd_tags,
        )
    else:
        tracer.enabled = False


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def to_pretty_json(value):
    return json.dumps(
        value, sort_keys=True, indent=4, separators=(",", ": "), default=default
    )


"""Initialize the flask app"""
api = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
)
api.jinja_env.filters["tojson_pretty"] = to_pretty_json
sock = Sock(api)
config.load_incluster_config()
initialize_datadog()

"""
For local mac docker image creation and testing, switch to host.docker.internal
"""
redis_host = os.getenv(
    "REDIS_HOST", default="dinghy-ping-redis.default.svc.cluster.local"
)

"""
Dinghy Ping Host name used for web socket connection to collect logs
"""
MY_APP_NAME = os.getenv("MY_APP_NAME", default="dinghy-ping")
MY_CLUSTER_DOMAIN = os.getenv("MY_CLUSTER_DOMAIN", default="localhost")

if MY_CLUSTER_DOMAIN == "localhost":
    # building ws host for localhost Tilt development over http
    dinghy_ping_web_socket_host = "ws://localhost:8080"
else:
    dinghy_ping_web_socket_host = f"wss://{MY_APP_NAME}.{MY_CLUSTER_DOMAIN}"

"""
AWS Region name, defaults to us-west-2
"""
region_name = os.getenv("AWS_DEFAULT_REGION", default="us-west-2")


@api.route("/health")
def dinghy_health():
    """Health check index page"""
    response = make_response("Ok", 200)
    return response


@api.route("/history")
def dinghy_history():
    """Return list of pinged history"""
    data = {"history": _get_all_pinged_urls()}
    response = make_response(jsonify(data), 200)
    return response


@api.route("/")
@datadog.statsd.timed(
    metric="dinghy_ping_events_home_page_load_time.timer", tags=dd_tags
)
def dinghy_html():
    """Index route to Dinghy-ping input html form"""
    result = render_template("index.html", get_all_pinged_urls=_get_all_pinged_urls())
    return result


@api.route("/ping/domains")
def ping_multiple_domains():
    """
    Async process to test multiple domains and return JSON with results
    Post request data example
    {
      "domains": [
        {
          "protocol": "https",
          "domain": "google.com",
          "headers: { "header1": "valule" }
        },
        {
          "protocol": "https",
          "domain": "microsoft.com"
        }
      ]
    }

    Return results
    {
      "domains": [
        {
          "protocol": "https",
          "domain": "google.com",
          "domain_response_code": "200",
          "domain_response_time_ms": "30.0ms"
          "
        },
        {
          "protocol": "https",
          "domain": "microsoft.com"
          "domain_response_code": "200",
          "domain_response_time_ms": "200.1ms"
        }
      ]
    }
    """

    results = []

    def build_domain_results(protocol, request_domain, results, headers):
        (
            response_code,
            response_text,
            response_time_ms,
            response_headers,
        ) = _process_request(protocol, request_domain, request.args, headers)
        results.append(
            {
                "protocol": protocol,
                "domain": request_domain,
                "domain_response_code": response_code,
                "domain_response_headers": response_headers,
                "domain_response_time_ms": response_time_ms,
            }
        )

    def gather_results(data):
        for domain in data["domains"]:
            protocol = domain["protocol"]
            request_domain = domain["domain"]
            headers = domain["headers"]
            build_domain_results(protocol, request_domain, results, headers)

    resp = {"domains_response_results": results, "wait": gather_results(request.data)}

    return jsonify(resp)


@api.route("/ping/{protocol}/{domain}")
def domain_response_html(*, protocol, domain):
    """
    API endpoint for sending a request to a domain via user specified protocol
    response containts status_code, body text and response_time_ms
    """

    headers = {}
    response_code, response_text, response_time_ms, response_headers = _process_request(
        protocol, domain, request.args, headers
    )

    resp = render_template(
        "ping_response.html",
        domain=domain,
        domain_response_code=response_code,
        domain_response_text=response_text,
        domain_response_headers=response_headers,
        domain_response_time_ms=response_time_ms,
    )

    return resp


@api.route("/form-input")
def form_input():
    """Dinghy-ping html input form for http connection"""
    url = urlparse(request.args["url"])
    if request.args["headers"]:
        print(f"here: {request.args['headers']}")
        headers = json.loads(request.args["headers"])
    else:
        headers = {}
    if url.scheme == "":
        scheme_notes = "Scheme not given, defaulting to https"
    else:
        scheme_notes = f"Scheme {url.scheme} provided"

    response_code, response_text, response_time_ms, response_headers = _process_request(
        url.scheme, url.netloc + url.path, url.query, headers
    )

    resp = render_template(
        "ping_response.html",
        request=f'{request.args["url"]}',
        scheme_notes=scheme_notes,
        domain_response_code=response_code,
        domain_response_text=response_text,
        domain_response_headers=response_headers,
        domain_response_time_ms=response_time_ms,
    )

    return resp


@api.route("/form-input-tcp-connection-test")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_tcp_response.timer", tags=dd_tags
)
async def form_input_tcp_connection_test():
    """Form input endpoint for tcp connection test"""
    logging.basicConfig(level=logging.DEBUG)
    tcp_endpoint = request.args["tcp-endpoint"]
    tcp_port = request.args["tcp-port"]

    try:
        reader, writer = await asyncio.open_connection(host=tcp_endpoint, port=tcp_port)
        conn_info = f"Connection created to {tcp_endpoint} on port {tcp_port}"
        d = DinghyData(
            redis_host,
            domain_response_code="tcp handshake success",
            domain_response_time_ms="N/A",
            request_url=f"{tcp_endpoint}:{tcp_port}",
        )
        d.save_ping()
        resp = render_template(
            "ping_response_tcp_conn.html",
            request=tcp_endpoint,
            port=tcp_port,
            connection_results=conn_info,
        )
    except (asyncio.TimeoutError, ConnectionRefusedError):
        print("Network port not responding")
        conn_info = f"Failed to connect to {tcp_endpoint} on port {tcp_port}"
        resp.status_code = make_response("error connecting to network port", 402)
        resp = render_template(
            "ping_response_tcp_conn.html",
            request=tcp_endpoint,
            port=tcp_port,
            connection_results=conn_info,
        )

    return resp


@api.route("/form-input-dns-info")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_dns_response.timer", tags=dd_tags
)
def form_input_dns_info():
    """Form input endpoint for dns info"""
    domain = request.args["domain"]

    nameserver = request.args.get("nameserver")

    dns_info_A = _gather_dns_A_info(domain, nameserver)
    dns_info_NS = _gather_dns_NS_info(domain, nameserver)
    dns_info_MX = _gather_dns_MX_info(domain, nameserver)

    resp = render_template(
        "dns_info.html",
        domain=domain,
        dns_info_A=dns_info_A,
        dns_info_NS=dns_info_NS,
        dns_info_MX=dns_info_MX,
    )

    return resp


@api.route("/get/deployment-details")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_deployment_details.timer", tags=dd_tags
)
def dinghy_get_deployment_details():
    """List deployments on the cluster"""
    namespace = request.args.get("namespace", "default")
    tail_lines = request.args.get("tail_lines", TAIL_LINES_DEFAULT)
    name = request.args.get("name")
    k8s_client = client.AppsV1Api()
    deployment = k8s_client.read_namespaced_deployment(name, namespace)

    # Find replica set
    replica_set_result = k8s_client.list_namespaced_replica_set(namespace)

    all_pods = {}
    replica_sets = []
    for rs in replica_set_result.items:
        if not bool(rs.status.replicas):
            continue
        deployment_ref = None
        for reference in rs.metadata.owner_references:
            if deployment.metadata.uid == reference.uid:
                deployment_ref = reference
                break
        rs_is_ready = rs.status.available_replicas == rs.status.ready_replicas
        if deployment_ref is not None and rs_is_ready:
            replica_sets.append(rs)

    try:
        pod_list = client.CoreV1Api().list_namespaced_pod(namespace, watch=False)
        for pod in pod_list.items:
            if pod.metadata.name.startswith(name):
                for rs in replica_sets:
                    if pod.metadata.name.startswith(rs.metadata.name):
                        all_pods[pod.metadata.name] = pod.to_dict()
    except Exception:
        logging.exception("List pods error")

    resp = render_template(
        "deployment_describe_output.html",
        deployment=deployment,
        all_pods=all_pods,
        tail_lines=tail_lines,
    )

    return resp


@api.route("/get/deployments")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_deployment_list.timer", tags=dd_tags
)
def dinghy_get_deployments():
    """List deployments on the cluster"""
    namespace = request.args.get("namespace")
    workloads_only = bool(request.args.get("workloads", False))
    name_filter = request.args.get("filter")

    if namespace is None:
        namespaces = _get_all_namespaces()
    else:
        namespaces = [namespace]

    deployments = []
    k8s_client = client.AppsV1Api()

    for namespace in namespaces:
        ret = k8s_client.list_namespaced_deployment(namespace)
        for i in ret.items:
            deployment = i.metadata.name
            if name_filter is not None and name_filter not in deployment:
                continue
            if workloads_only and namespace.startswith("kube"):
                continue
            if workloads_only and namespace.startswith("docker"):
                continue
            namespace = i.metadata.namespace
            deployments.append(
                {
                    "name": deployment,
                    "namespace": namespace,
                    "revision": i.metadata.generation,
                    "date": i.metadata.creation_timestamp,
                    "status": i.status,
                }
            )

    resp = render_template("deployments_tabbed.html", deployments=deployments)

    return resp


@api.route("/list-pods")
@datadog.statsd.timed(metric="dinghy_ping_events_get_pod_list.timer", tags=dd_tags)
def list_pods():
    """Route to list pods"""
    namespace = request.args["namespace"]
    ret = []

    try:
        ret = _get_all_pods(namespace)
    except Exception:
        traceback.print_exc(file=sys.stdout)

    resp = jsonify({"pods": ret})

    return resp


@api.route("/get/pods")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_list_pod_list.timer", tags=dd_tags
)
def dinghy_get_pods():
    """Form input page for pod logs and describe, input namespace"""

    resp = render_template("pods_tabbed.html", namespaces=_get_all_namespaces())

    return resp


@api.route("/get/events")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_namespace_event_page.timer", tags=dd_tags
)
def dinghy_get_namespace_events():
    """Render landing page to select namespace for event stream"""

    all_namespaces = _get_all_namespaces()

    resp = render_template("events_tabbed.html", namespaces=all_namespaces)

    return resp


@api.route("/get/pod-details")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_pod_details.timer", tags=dd_tags
)
def dinghy_get_pod_details():
    """Landing page for Dinghy-ping pod logs input html form"""
    namespace = request.args.get("namespace", default="default")
    tail_lines = request.args.get("tail_lines", default=TAIL_LINES_DEFAULT)
    name_filter = request.args.get("filter")
    pods = {}
    all_pods = _get_all_pods(namespace=namespace)
    if name_filter is not None:
        for pod, namespace in all_pods.items():
            if name_filter in pod:
                pods[pod] = namespace
    else:
        pods = all_pods

    resp = render_template("pod_logs_input.html", all_pods=pods, tail_lines=tail_lines)

    return resp


@api.route("/input-pod-logs")
@datadog.statsd.timed(metric="dinghy_ping_events_display_pod_logs.timer", tags=dd_tags)
def form_input_pod_logs():
    """List pods in namespace and click on one to display logs"""
    pod = request.args.get("pod")
    namespace = request.args.get("namespace", "default")
    tail_lines = request.args.get("tail_lines", TAIL_LINES_DEFAULT)

    logging.debug(f"Retrieving pod logs... {pod} in namespace {namespace}")

    try:
        ret = _get_pod_logs(pod, namespace, tail_lines)
        resp = render_template("pod_logs_output.html", logs=ret)

        return resp
    except Exception:
        traceback.print_exc(file=sys.stdout)


@api.route("/input-pod-logs-stream")
@datadog.statsd.timed(
    metric="dinghy_ping_events_display_pod_logs_stream.timer", tags=dd_tags
)
def form_input_pod_logs_stream(*, tail_lines=TAIL_LINES_DEFAULT):
    """List pods in namespace and click on one to display logs"""
    pod = request.args["pod"]
    namespace = request.args["namespace"]

    resp = render_template(
        "pod_logs_output_streaming.html",
        namespace=namespace,
        name=pod,
        dinghy_ping_web_socket_host=dinghy_ping_web_socket_host,
    )

    return resp


@api.route("/event-stream/<namespace>/<filter>")
@datadog.statsd.timed(
    metric="dinghy_ping_events_display_namespace_events_stream.timer", tags=dd_tags
)
def namespace_event_stream(namespace, filter):
    """Render page with streaming events in namespace,
    default to just Pod events, optional all events"""

    logging.info(f"filter: {filter}")

    resp = render_template(
        "events_output_streaming.html",
        namespace=namespace,
        filter=filter,
        dinghy_ping_web_socket_host=dinghy_ping_web_socket_host,
    )

    return resp


@sock.route("/ws/logstream")
@datadog.statsd.timed(
    metric="dinghy_ping_events_web_socket_duration.timer", tags=dd_tags
)
def log_stream_websocket(ws):
    k8s_client = client.CoreV1Api()

    name = request.args["name"]
    namespace = request.args["namespace"]

    resp = k8s_client.read_namespaced_pod_log(
        name,
        namespace,
        tail_lines=TAIL_LINES_DEFAULT,
        follow=True,
        _preload_content=False,
    )
    while True:
        try:
            line = resp.readline()
        except asyncio.TimeoutError as e:
            logging.error(
                f"""
            Async timeout server side, will recover from client side {e}
            """
            )
            break
        if not line:
            break
        ws.send(line.decode("utf-8"))

    ws.close()


@sock.route("/ws/event-stream")
@datadog.statsd.timed(
    metric="dinghy_ping_events_web_socket_duration.timer", tags=dd_tags
)
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

    w.stop()
    ws.close()


@api.route("/pod-describe")
@datadog.statsd.timed(
    metric="dinghy_ping_events_render_pod_description.timer", tags=dd_tags
)
def dinghy_pod_describe():
    """Describe given pod and display response"""
    pod = request.args["pod"]
    namespace = request.args["namespace"]
    described = _describe_pod(pod, namespace)
    events = _get_pod_events(pod, namespace)

    resp = render_template(
        "pod_describe_output.html",
        described=described,
        pod=pod,
        namespace=namespace,
        events=events,
    )

    return resp


@api.route("/api/pod-events/{namespace}/{pod}")
def dinghy_pod_events(*, namespace, pod):
    """Return pod events"""
    events = _get_pod_events(pod, namespace)
    # Normalize events, ie serialize datetime
    events_normalized = json.dumps(events, default=default)

    resp = jsonify(events_normalized)

    return resp


@api.route("/deployment-logs/{namespace}/{name}")
def dinghy_deployment_logs(
    *, namespace, name, tail_lines=TAIL_LINES_DEFAULT, preview=LOGS_PREVIEW_LENGTH
):
    """Get pod logs for a given deployment"""
    tail_lines = request.args.get("tail_lines", tail_lines)
    logs = _get_deployment_logs(namespace, name, tail_lines)
    logs_preview = logs[0:preview]

    if "json" in request.args.keys():
        if "preview" in request.args.keys():
            resp = jsonify({"logs": logs_preview})
        else:
            resp = jsonify({"logs": logs})
    else:
        resp = render_template("pod_logs_output.html", logs=logs)

    return resp


def _get_deployment_logs(namespace, name, tail_lines=TAIL_LINES_DEFAULT):
    """Gather pod names via K8s label selector"""
    pods = []
    k8s_client = client.CoreV1Api()

    try:
        api_response = k8s_client.list_namespaced_pod(
            namespace, label_selector="release={}".format(name)
        )
        for api_items in api_response.items:
            pods.append(api_items.metadata.name)
    except ApiException as e:
        logging.error(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")

    # Iterate over list of pods and concatenate logs
    logs = ""
    try:
        for pod in pods:
            logs += pod + "\n"
            logs += k8s_client.read_namespaced_pod_log(
                pod, namespace, tail_lines=tail_lines
            )
    except ApiException as e:
        logging.error(f"Exception when calling CoreV1Api->read_namespaced_pod_log: {e}")

    return logs


def _get_pod_logs(pod, namespace, tail_lines=TAIL_LINES_DEFAULT):
    """Read pod logs"""
    k8s_client = client.CoreV1Api()
    ret = []
    try:
        ret = k8s_client.read_namespaced_pod_log(
            pod, namespace, tail_lines=TAIL_LINES_DEFAULT
        )
    except ApiException as e:
        logging.error(f"Exception when calling CoreV1Api->read_namespaced_pod_log: {e}")

    return ret


def _describe_pod(pod, namespace):
    """Describes pod"""
    k8s_client = client.CoreV1Api()

    try:
        ret = k8s_client.read_namespaced_pod(pod, namespace, pretty="true")
    except ApiException as e:
        logging.exception(f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")
        ret = {}
    return ret


def _get_pod_events(pod, namespace):
    """Get pod events"""
    k8s_client = client.CoreV1Api()
    events = {}

    try:
        ret_events = k8s_client.list_namespaced_event(
            field_selector=f"involvedObject.name={pod}", namespace=namespace
        )
    except ApiException as e:
        logging.error(f"Exception when calling CoreV1Api->list_namespaced_event: {e}")

    logging.debug(f"found events: {ret_events.items}")
    for counter, event in enumerate(ret_events.items):
        events[counter] = dict(
            Type=event.type,
            Reason=event.reason,
            From=event.reporting_component,
            Age=event.last_timestamp,
            Message=event.message,
        )

    return events


def _get_all_namespaces():
    """Get all namespaces"""
    k8s_client = client.CoreV1Api()
    namespaces = []

    ret = k8s_client.list_namespace(watch=False)
    for i in ret.items:
        namespaces.append(i.metadata.name)

    return namespaces


def _get_all_pods(namespace=None):
    """Get all pods"""
    pods = {}
    k8s_client = client.CoreV1Api()

    if namespace:
        ret = k8s_client.list_namespaced_pod(namespace, watch=False)
    else:
        ret = k8s_client.list_pod_for_all_namespaces(watch=False)

    for i in ret.items:
        pod = i.metadata.name
        namespace = i.metadata.namespace
        pods.update({pod: i.metadata.namespace})

    return pods


def _gather_dns_A_info(domain, nameserver):
    dns_info_A = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.A, nameserver=nameserver
    )
    return dns_info_A.dns_query()


def _gather_dns_NS_info(domain, nameserver):
    dns_info_NS = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.NS, nameserver=nameserver
    )
    return dns_info_NS.dns_query()


def _gather_dns_MX_info(domain, nameserver):
    dns_info_MX = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.MX, nameserver=nameserver
    )
    return dns_info_MX.dns_query()


def _process_request(protocol, domain, params, headers):
    """
    Internal method to run request process, takes protocol and domain for input
    """

    if protocol == "":
        protocol = "https"

    domain_response_code = ""
    domain_response_text = ""
    domain_response_time_ms = ""
    domain_response_headers = {}

    try:
        # Count how many times a user requests an HTTP check
        datadog.statsd.increment(
            "dinghy_ping_http_connection_check.increment", tags=dd_tags
        )
        r = requests.get(
            f"{protocol}://{domain}", params=params, timeout=5, headers=headers
        )
    except requests.exceptions.Timeout as err:
        domain_response_text = f"Timeout: {err}"
        # Count how many times a user requests a TCP check
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_timeout.increment",
            tags=dd_tags,
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )
    except requests.exceptions.TooManyRedirects as err:
        domain_response_text = f"TooManyRedirects: {err}"
        # Count how many times a user gets TooManyRedirect response
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_redirects.increment",
            tags=dd_tags,
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )
    except requests.exceptions.RequestException as err:
        domain_response_text = f"RequestException: {err}"
        # Count how many times a user get a request exception with their check
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_exception.increment",
            tags=dd_tags,
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_headers = dict(r.headers)
    domain_response_time_ms = r.elapsed.microseconds / 1000

    d = DinghyData(redis_host, domain_response_code, domain_response_time_ms, r.url)
    d.save_ping()

    return (
        domain_response_code,
        domain_response_text,
        domain_response_time_ms,
        domain_response_headers,
    )


def _get_all_pinged_urls():
    """Get pinged URLs from Dinghy-ping data module"""
    p = DinghyData(redis_host)
    return p.get_all_pinged_urls()
