import json
import logging
import sys
import traceback

import datadog
from flask import current_app, jsonify, make_response, render_template, request
from kubernetes import client

from app.main import bp
from app.main.forms import DNSCheckForm, HTTPCheckForm, TCPCheckForm
from app.utils.k8s import (
    describe_pod,
    get_all_namespaces,
    get_all_pods,
    get_deployment_logs,
    get_pod_events,
    get_pod_logs,
)
from app.utils.network import (
    dns_check,
    get_all_pinged_urls,
    http_check,
    process_request,
    tcp_check,
)

from .. import default


@bp.route("/health")
def dinghy_health():
    """Health check index page"""
    response = make_response("Ok", 200)
    return response


@bp.route("/history")
def dinghy_history():
    """Return list of pinged history"""
    data = {"history": get_all_pinged_urls(current_app.config["REDIS_HOST"])}
    response = make_response(jsonify(data), 200)
    return response


@bp.route("/", methods=["GET", "POST"])
@datadog.statsd.timed(metric="dinghy_ping_events_home_page_load_time.timer")
def dinghy_html():
    """Index route to Dinghy-ping input html form"""
    http_form = HTTPCheckForm()
    dns_form = DNSCheckForm()
    tcp_form = TCPCheckForm()
    urls = get_all_pinged_urls(current_app.config["REDIS_HOST"])

    if http_form.validate_on_submit():
        url = http_form.url.data
        headers = http_form.headers.data
        (
            response_code,
            response_text,
            response_time_ms,
            response_headers,
            request_url,
        ) = http_check(url, headers, current_app.config["REDIS_HOST"])
        return render_template(
            "ping_response.html",
            request=request_url,
            domain_response_code=response_code,
            domain_response_text=response_text,
            domain_response_headers=response_headers,
            domain_response_time_ms=response_time_ms,
        )

    if dns_form.validate_on_submit():
        domain = dns_form.domain.data
        nameserver = dns_form.nameserver.data

        dns_info_A, dns_info_NS, dns_info_MX = dns_check(
            domain, nameserver, current_app.config["REDIS_HOST"]
        )

        return render_template(
            "dns_info.html",
            domain=domain,
            dns_info_A=dns_info_A,
            dns_info_NS=dns_info_NS,
            dns_info_MX=dns_info_MX,
        )

    if tcp_form.validate_on_submit():
        tcp_endpoint = tcp_form.tcp_endpoint.data
        tcp_port = tcp_form.tcp_port.data
        conn_info = tcp_check(tcp_endpoint, tcp_port, current_app.config["REDIS_HOST"])
        return render_template(
            "ping_response_tcp_conn.html",
            request=tcp_endpoint,
            port=tcp_port,
            connection_results=conn_info,
        )

    return render_template(
        "index.html",
        http_form=http_form,
        dns_form=dns_form,
        tcp_form=tcp_form,
        get_all_pinged_urls=urls,
    )


@bp.route("/ping/domains", methods=["POST"])
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
        ) = process_request(
            protocol,
            request_domain,
            request.args,
            headers,
            current_app.config["REDIS_HOST"],
        )
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


@bp.route("/ping/<protocol>/<path:domain>")
def domain_response_html(*, protocol, domain):
    """
    API endpoint for sending a request to a domain via user specified protocol
    response containts status_code, body text and response_time_ms
    """

    headers = {}
    response_code, response_text, response_time_ms, response_headers = process_request(
        protocol, domain, request.args, headers, current_app.config["REDIS_HOST"]
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


@bp.route("/get/deployment-details")
@datadog.statsd.timed(metric="dinghy_ping_events_render_deployment_details.timer")
def dinghy_get_deployment_details():
    """List deployments on the cluster"""
    namespace = request.args.get("namespace", "default")
    tail_lines = request.args.get(
        "tail_lines", current_app.config["TAIL_LINES_DEFAULT"]
    )
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


@bp.route("/get/deployments")
@datadog.statsd.timed(metric="dinghy_ping_events_render_deployment_list.timer")
def dinghy_get_deployments():
    """List deployments on the cluster"""
    namespace = request.args.get("namespace")
    workloads_only = bool(request.args.get("workloads", False))
    name_filter = request.args.get("filter")

    if namespace is None:
        namespaces = get_all_namespaces()
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


@bp.route("/list-pods")
@datadog.statsd.timed(metric="dinghy_ping_events_get_pod_list.timer")
def list_pods():
    """Route to list pods"""
    namespace = request.args["namespace"]
    ret = []

    try:
        ret = get_all_pods(namespace)
    except Exception:
        traceback.print_exc(file=sys.stdout)

    resp = jsonify({"pods": ret})

    return resp


@bp.route("/get/pods")
@datadog.statsd.timed(metric="dinghy_ping_events_render_list_pod_list.timer")
def dinghy_get_pods():
    """Form input page for pod logs and describe, input namespace"""
    tail_lines = int(
        request.args.get("tail_lines", default=current_app.config["TAIL_LINES_DEFAULT"])
    )
    resp = render_template(
        "pods_tabbed.html", tail_lines=tail_lines, namespaces=get_all_namespaces()
    )

    return resp


@bp.route("/get/events")
@datadog.statsd.timed(metric="dinghy_ping_events_render_namespace_event_page.timer")
def dinghy_get_namespace_events():
    """render landing page to select namespace for event stream"""

    all_namespaces = get_all_namespaces()

    resp = render_template("events_tabbed.html", namespaces=all_namespaces)

    return resp


@bp.route("/get/pod-details")
@datadog.statsd.timed(metric="dinghy_ping_events_render_pod_details.timer")
def dinghy_get_pod_details():
    """Landing page for Dinghy-ping pod logs input html form"""
    namespace = request.args.get("namespace", default="default")
    tail_lines = request.args.get(
        "tail_lines", default=current_app.config["TAIL_LINES_DEFAULT"]
    )
    name_filter = request.args.get("filter")
    pods = {}
    all_pods = get_all_pods(namespace=namespace)
    if name_filter is not None:
        for pod, namespace in all_pods.items():
            if name_filter in pod:
                pods[pod] = namespace
    else:
        pods = all_pods

    resp = render_template("pod_logs_input.html", all_pods=pods, tail_lines=tail_lines)

    return resp


@bp.route("/input-pod-logs")
@datadog.statsd.timed(metric="dinghy_ping_events_display_pod_logs.timer")
def form_input_pod_logs():
    """List pods in namespace and click on one to display logs"""
    pod = request.args.get("pod")
    namespace = request.args.get("namespace", "default")
    tail_lines = request.args.get(
        "tail_lines", current_app.config["TAIL_LINES_DEFAULT"]
    )
    container = request.args.get("container", "")
    logging.debug(f"Retrieving pods... {pod} in namespace {namespace}")
    logging.debug(f"Retrieving container logs... {container} in pod {pod}")

    try:
        ret = get_pod_logs(pod, namespace, container, tail_lines)
        resp = render_template("pod_logs_output.html", logs=ret)

        return resp
    except Exception:
        traceback.print_exc(file=sys.stdout)


@bp.route("/input-pod-logs-stream")
@datadog.statsd.timed(metric="dinghy_ping_events_display_pod_logs_stream.timer")
def form_input_pod_logs_stream(*, tail_lines=None):
    """List pods in namespace and click on one to display logs"""
    tail_lines = tail_lines or current_app.config["TAIL_LINES_DEFAULT"]
    pod = request.args["pod"]
    namespace = request.args["namespace"]
    container = request.args.get("container", "")

    resp = render_template(
        "pod_logs_output_streaming.html",
        namespace=namespace,
        name=pod,
        container=container,
        dinghy_ping_web_socket_host=current_app.config["DINGHY_PING_WEB_SOCKET_HOST"],
    )

    return resp


@bp.route("/event-stream/<namespace>/<filter>")
@datadog.statsd.timed(metric="dinghy_ping_events_display_namespace_events_stream.timer")
def namespace_event_stream(namespace, filter):
    """Render page with streaming events in namespace,
    default to just Pod events, optional all events"""

    logging.info(f"filter: {filter}")

    resp = render_template(
        "events_output_streaming.html",
        namespace=namespace,
        filter=filter,
        dinghy_ping_web_socket_host=current_app.config["DINGHY_PING_WEB_SOCKET_HOST"],
    )

    return resp


@bp.route("/pod-describe")
@datadog.statsd.timed(metric="dinghy_ping_events_render_pod_description.timer")
def dinghy_pod_describe():
    """Describe given pod and display response"""
    pod = request.args["pod"]
    namespace = request.args["namespace"]
    described = describe_pod(pod, namespace)
    events = get_pod_events(pod, namespace)

    resp = render_template(
        "pod_describe_output.html",
        described=described,
        pod=pod,
        namespace=namespace,
        events=events,
    )

    return resp


@bp.route("/api/pod-events/<namespace>/<pod>")
def dinghy_pod_events(*, namespace, pod):
    """Return pod events"""
    events = get_pod_events(pod, namespace)
    # Normalize events, ie serialize datetime
    events_normalized = json.dumps(events, default=default)

    resp = jsonify(events_normalized)

    return resp


@bp.route("/deployment-logs/<namespace>/<name>")
def dinghy_deployment_logs(*, namespace, name, tail_lines, preview):
    """Get pod logs for a given deployment"""
    logs = get_deployment_logs(
        namespace, name, current_app.config["TAIL_LINES_DEFAULT"]
    )
    logs_preview = logs[0:preview]

    if "json" in request.args.keys():
        if "preview" in request.args.keys():
            resp = jsonify({"logs": logs_preview})
        else:
            resp = jsonify({"logs": logs})
    else:
        resp = render_template("pod_logs_output.html", logs=logs)

    return resp
