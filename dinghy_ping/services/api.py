import asyncio
import datadog
import datetime
import dns.rdatatype
import json
import logging
import os
import sys
import responder
import traceback
from urllib.parse import urlparse
from kubernetes_asyncio import client, config, watch
from kubernetes_asyncio.client.rest import ApiException
from dinghy_ping.models.data import DinghyData
from dinghy_ping.models import dinghy_dns
from ddtrace import tracer

# http://pypi.datadoghq.com/trace/docs/other_integrations.html#requests
from ddtrace import patch
patch(requests=True)
import requests # noqa

logging.basicConfig(level=logging.DEBUG)

TAIL_LINES_DEFAULT = 100
LOGS_PREVIEW_LENGTH = 1000
TEMPLATE_DIR = 'dinghy_ping/views/templates/'
STATIC_DIR = 'dinghy_ping/views/static/'

environment = os.getenv("ENVIRONMENT", "none")
dd_tags = [f"environment={environment}"]


def initialize_datadog():
    dd_host = os.getenv('DD_AGENT_HOST', 'host.docker.internal')
    dd_statsd_port = os.getenv('DD_DOGSTATSD_PORT', '8125')
    dd_trace_agent_hostname = os.getenv(
        'DD_TRACE_AGENT_HOSTNAME', 'host.docker.internal')
    dd_trace_agent_port = os.getenv('DD_TRACE_AGENT_PORT', '8126')

    datadog_options = {
        'statsd_host': dd_host,
        'statsd_port': dd_statsd_port
    }

    datadog.initialize(**datadog_options)

    tracer.configure(
        hostname=dd_trace_agent_hostname,
        port=dd_trace_agent_port,
    )


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '),
                      default=default)


api = responder.API(
    title="Dinghy Ping",
    templates_dir=TEMPLATE_DIR,
    static_dir=STATIC_DIR,
    version="1.0",
    openapi="3.0.0",
    docs_route="/docs"
    )

api.jinja_env.filters['tojson_pretty'] = to_pretty_json

"""
For local mac docker image creation and testing, switch to host.docker.internal
"""
redis_host = os.getenv("REDIS_HOST", default="127.0.0.1")

"""
Dinghy Ping Host name used for web socket connection to collect logs
"""
MY_APP_NAME = os.getenv("MY_APP_NAME", default="dinghy-ping")
MY_CLUSTER_DOMAIN = os.getenv("MY_CLUSTER_DOMAIN", default="localhost")

dinghy_ping_host = f"{MY_APP_NAME}.{MY_CLUSTER_DOMAIN}"

"""
AWS Region name, defaults to us-west-2
"""
region_name = os.getenv("AWS_DEFAULT_REGION", default='us-west-2')


@api.route("/health")
def dinghy_health(req, resp):
    """Health check index page"""
    resp.text = "Ok"


@api.route("/history")
def dinghy_history(req, resp):
    """Return list of pinged history"""
    resp.media = {
        "history": _get_all_pinged_urls()
    }


@api.route("/")
@datadog.statsd.timed(
        metric='dinghy_ping_events_home_page_load_time.timer', tags=dd_tags)
def dinghy_html(req, resp):
    """Index route to Dinghy-ping input html form"""
    resp.content = api.template(
        'index.html',
        get_all_pinged_urls=_get_all_pinged_urls()
    )


@api.route("/ping/domains")
async def ping_multiple_domains(req, resp):
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
        response_code, response_text, response_time_ms, response_headers = (
            _process_request(protocol, request_domain, req.params, headers)
        )
        results.append({
            "protocol": protocol,
            "domain": request_domain,
            "domain_response_code": response_code,
            "domain_response_headers": response_headers,
            "domain_response_time_ms": response_time_ms
        })

    def gather_results(data):
        for domain in data['domains']:
            protocol = domain['protocol']
            request_domain = domain['domain']
            headers = domain['headers']
            build_domain_results(protocol, request_domain, results, headers)

    resp.media = {
        "domains_response_results": results,
        "wait": gather_results(await req.media())
        }


@api.route("/ping/{protocol}/{domain}")
def domain_response_html(req, resp, *, protocol, domain):
    """
    API endpoint for sending a request to a domain via user specified protocol
    response containts status_code, body text and response_time_ms
    """

    headers = {}
    response_code, response_text, response_time_ms, response_headers = (
        _process_request(protocol, domain, req.params, headers)
    )

    resp.content = api.template(
            'ping_response.html',
            domain=domain,
            domain_response_code=response_code,
            domain_response_text=response_text,
            domain_response_headers=response_headers,
            domain_response_time_ms=response_time_ms
    )


@api.route("/form-input")
def form_input(req, resp):
    """Dinghy-ping html input form for http connection"""
    url = urlparse(req.params['url'])
    if 'headers' in req.params.keys():
        headers = json.loads(req.params['headers'])
    else:
        headers = {}
    if url.scheme == "":
        scheme_notes = "Scheme not given, defaulting to https"
    else:
        scheme_notes = f'Scheme {url.scheme} provided'

    response_code, response_text, response_time_ms, response_headers = (
        _process_request(url.scheme, url.netloc + url.path, url.query, headers)
    )

    resp.content = api.template(
            'ping_response.html',
            request=f'{req.params["url"]}',
            scheme_notes=scheme_notes,
            domain_response_code=response_code,
            domain_response_text=response_text,
            domain_response_headers=response_headers,
            domain_response_time_ms=response_time_ms
    )


@api.route("/form-input-tcp-connection-test")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_tcp_response.timer', tags=dd_tags)
async def form_input_tcp_connection_test(req, resp):
    """Form input endpoint for tcp connection test"""
    logging.basicConfig(level=logging.DEBUG)
    tcp_endpoint = req.params['tcp-endpoint']
    tcp_port = req.params['tcp-port']

    try:
        reader, writer = await asyncio.open_connection(
            host=tcp_endpoint, port=tcp_port
            )
        conn_info = f'Connection created to {tcp_endpoint} on port {tcp_port}'
        d = DinghyData(
            redis_host,
            domain_response_code="tcp handshake success",
            domain_response_time_ms="N/A",
            request_url=f'{tcp_endpoint}:{tcp_port}'
        )
        d.save_ping()
        resp.content = api.template(
            'ping_response_tcp_conn.html',
            request=tcp_endpoint,
            port=tcp_port,
            connection_results=conn_info
        )
    except (asyncio.TimeoutError, ConnectionRefusedError):
        print("Network port not responding")
        conn_info = f'Failed to connect to {tcp_endpoint} on port {tcp_port}'
        resp.status_code = api.status_codes.HTTP_402
        resp.content = api.template(
            'ping_response_tcp_conn.html',
            request=tcp_endpoint,
            port=tcp_port,
            connection_results=conn_info
        )


@api.route("/form-input-dns-info")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_dns_response.timer', tags=dd_tags)
async def form_input_dns_info(req, resp):
    """Form input endpoint for dns info"""
    domain = req.params['domain']

    nameserver = req.params.get('nameserver')

    dns_info_A = _gather_dns_A_info(domain, nameserver)
    dns_info_NS = _gather_dns_NS_info(domain, nameserver)
    dns_info_MX = _gather_dns_MX_info(domain, nameserver)

    resp.content = api.template(
            'dns_info.html',
            domain=domain,
            dns_info_A=dns_info_A,
            dns_info_NS=dns_info_NS,
            dns_info_MX=dns_info_MX
    )


@api.route("/get/deployment-details")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_deployment_details.timer',
        tags=dd_tags)
async def dinghy_get_deployment_details(req, resp):
    """List deployments on the cluster"""
    namespace = req.params.get('namespace', 'default')
    tail_lines = req.params.get('tail_lines', TAIL_LINES_DEFAULT)
    name = req.params.get('name')
    k8s_client = client.AppsV1Api()
    deployment = await k8s_client.read_namespaced_deployment(name, namespace)

    # Find replica set
    replica_set_result = await k8s_client.list_namespaced_replica_set(
        namespace)

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
        pod_list = await client.CoreV1Api().list_namespaced_pod(
            namespace,
            watch=False)
        for pod in pod_list.items:
            if pod.metadata.name.startswith(name):
                for rs in replica_sets:
                    if pod.metadata.name.startswith(rs.metadata.name):
                        all_pods[pod.metadata.name] = pod.to_dict()
    except Exception:
        logging.exception('List pods error')

    resp.content = api.template(
        'deployment_describe_output.html',
        deployment=deployment,
        all_pods=all_pods,
        tail_lines=tail_lines
    )


@api.route("/get/deployments")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_deployment_list.timer',
        tags=dd_tags)
async def dinghy_get_deployments(req, resp):
    """List deployments on the cluster"""
    namespace = req.params.get('namespace')
    workloads_only = bool(req.params.get('workloads', False))
    name_filter = req.params.get('filter')

    if namespace is None:
        namespaces = await _get_all_namespaces()
    else:
        namespaces = [namespace]

    deployments = []
    k8s_client = client.AppsV1Api()

    for namespace in namespaces:
        ret = await k8s_client.list_namespaced_deployment(
            namespace)
        for i in ret.items:
            deployment = i.metadata.name
            if name_filter is not None and name_filter not in deployment:
                continue
            if workloads_only and namespace.startswith('kube'):
                continue
            if workloads_only and namespace.startswith('docker'):
                continue
            namespace = i.metadata.namespace
            deployments.append({'name': deployment,
                                'namespace': namespace,
                                'revision': i.metadata.generation,
                                'date': i.metadata.creation_timestamp,
                                'status': i.status})

    resp.content = api.template(
        'deployments_tabbed.html',
        deployments=deployments
    )


@api.route("/list-pods")
@datadog.statsd.timed(
        metric='dinghy_ping_events_get_pod_list.timer',
        tags=dd_tags)
async def list_pods(req, resp):
    """Route to list pods"""
    namespace = req.params['namespace']
    ret = []

    try:
        ret = await _get_all_pods(namespace)
    except Exception:
        traceback.print_exc(file=sys.stdout)

    resp.media = {"pods": ret}


@api.route("/get/pods")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_list_pod_list.timer', tags=dd_tags)
async def dinghy_get_pods(req, resp):
    """Form input page for pod logs and describe, input namespace"""

    resp.content = api.template(
        'pods_tabbed.html',
        namespaces=await _get_all_namespaces()
    )


@api.route("/get/events")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_namespace_event_page.timer',
        tags=dd_tags)
async def dinghy_get_namespace_events(req, resp):
    """Render landing page to select namespace for event stream"""

    all_namespaces = await _get_all_namespaces()

    resp.content = api.template(
        'events_tabbed.html',
        namespaces=all_namespaces
    )


@api.route("/get/pod-details")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_pod_details.timer', tags=dd_tags)
async def dinghy_get_pod_details(
        req, resp, namespace="default", tail_lines=TAIL_LINES_DEFAULT):
    """Landing page for Dinghy-ping pod logs input html form"""
    namespace = req.params.get('namespace')
    tail_lines = req.params.get('tail_lines', tail_lines)
    name_filter = req.params.get('filter')
    pods = {}
    all_pods = await _get_all_pods(namespace=namespace)
    if name_filter is not None:
        for pod, namespace in all_pods.items():
            if name_filter in pod:
                pods[pod] = namespace
    else:
        pods = all_pods

    resp.content = api.template(
        'pod_logs_input.html',
        all_pods=pods,
        tail_lines=tail_lines
    )


@api.route("/input-pod-logs")
@datadog.statsd.timed(
        metric='dinghy_ping_events_display_pod_logs.timer', tags=dd_tags)
async def form_input_pod_logs(req, resp, *, tail_lines=TAIL_LINES_DEFAULT):
    """List pods in namespace and click on one to display logs"""
    pod = req.params.get('pod')
    namespace = req.params.get('namespace', 'default')
    tail_lines = req.params.get('tail_lines', tail_lines)

    logging.debug(f"Retrieving pod logs... {pod} in namespace {namespace}")

    try:
        ret = await _get_pod_logs(pod, namespace, tail_lines)
        resp.content = api.template(
            'pod_logs_output.html',
            logs=ret
        )
    except Exception:
        traceback.print_exc(file=sys.stdout)


@api.route("/input-pod-logs-stream")
@datadog.statsd.timed(
        metric='dinghy_ping_events_display_pod_logs_stream.timer',
        tags=dd_tags)
async def form_input_pod_logs_stream(
        req, resp, *, tail_lines=TAIL_LINES_DEFAULT):
    """List pods in namespace and click on one to display logs"""
    pod = req.params['pod']
    namespace = req.params['namespace']

    resp.content = api.template(
        'pod_logs_output_streaming.html',
        namespace=namespace,
        name=pod,
        dinghy_ping_host=dinghy_ping_host
    )


@api.route("/event-stream/{namespace}/{filter}")
@datadog.statsd.timed(
        metric='dinghy_ping_events_display_namespace_events_stream.timer',
        tags=dd_tags)
async def namespace_event_stream(
        req, resp, *, namespace, filter):
    """Render page with streaming events in namespace,
    default to just Pod events, optional all events"""

    logging.info(f'filter: {filter}')

    resp.content = api.template(
        'events_output_streaming.html',
        namespace=namespace,
        filter=filter,
        dinghy_ping_host=dinghy_ping_host
    )


@api.route("/ws/logstream", websocket=True)
@datadog.statsd.timed(
        metric='dinghy_ping_events_web_socket_duration.timer', tags=dd_tags)
async def log_stream_websocket(ws):
    k8s_client = client.CoreV1Api()

    name = ws.query_params['name']
    namespace = ws.query_params['namespace']

    await ws.accept()
    resp = await k8s_client.read_namespaced_pod_log(
        name,
        namespace,
        tail_lines=TAIL_LINES_DEFAULT,
        follow=True, _preload_content=False
        )
    while True:
        try:
            line = await resp.content.readline()
        except asyncio.TimeoutError as e:
            logging.error(
                f"""
            Async timeout server side, will recover from client side {e}
            """)
            break
        if not line:
            break
        await ws.send_text(line.decode('utf-8'))

    await ws.close()


@api.route("/ws/event-stream", websocket=True)
@datadog.statsd.timed(
        metric='dinghy_ping_events_web_socket_duration.timer', tags=dd_tags)
async def event_stream_websocket(ws):
    await ws.accept()
    namespace = ws.query_params['namespace']
    filter = ws.query_params['filter']

    if filter == 'all':
        field_selector = ""
    elif filter == "pod":
        field_selector = "involvedObject.kind=Pod"
    else:
        logging.info('event-stream filter is defaulting to all events')
        field_selector = ""

    v1 = client.CoreV1Api()
    w = watch.Watch()

    async for event in w.stream(
            v1.list_namespaced_event,
            namespace,
            field_selector=field_selector):
        obj = event['object']
        event_resp = dict(
                Name=obj.metadata.name,
                Message=obj.message)

        event_resp_json_dump = json.dumps(event_resp, default=default)
        # await ws.send_text(f"{obj.metadata.name}: {obj.message}")
        await ws.send_text(event_resp_json_dump)

    w.stop()
    ws.close()


@api.route("/pod-describe")
@datadog.statsd.timed(
        metric='dinghy_ping_events_render_pod_description.timer', tags=dd_tags)
async def dinghy_pod_describe(req, resp):
    """Describe given pod and display response"""
    pod = req.params['pod']
    namespace = req.params['namespace']
    described = await _describe_pod(pod, namespace)
    events = await _get_pod_events(pod, namespace)

    resp.content = api.template(
        'pod_describe_output.html',
        described=described,
        pod=pod,
        namespace=namespace,
        events=events
    )


@api.route("/api/pod-events/{namespace}/{pod}")
async def dinghy_pod_events(req, resp, *, namespace, pod):
    """Return pod events"""
    events = await _get_pod_events(pod, namespace)
    # Normalize events, ie serialize datetime
    events_normalized = json.dumps(events, default=default)

    resp.media = json.loads(events_normalized)


@api.route("/deployment-logs/{namespace}/{name}")
async def dinghy_deployment_logs(
                            req, resp, *,
                            namespace, name,
                            tail_lines=TAIL_LINES_DEFAULT,
                            preview=LOGS_PREVIEW_LENGTH):
    """Get pod logs for a given deployment"""
    tail_lines = req.params.get('tail_lines', tail_lines)
    logs = await _get_deployment_logs(namespace, name, tail_lines)
    logs_preview = logs[0:preview]

    if 'json' in req.params.keys():
        if 'preview' in req.params.keys():
            resp.media = {"logs": logs_preview}
        else:
            resp.media = {"logs": logs}
    else:
        resp.content = api.template(
            'pod_logs_output.html',
            logs=logs
        )


async def _get_deployment_logs(namespace, name, tail_lines=TAIL_LINES_DEFAULT):
    """Gather pod names via K8s label selector"""
    pods = []
    k8s_client = client.CoreV1Api()

    try:
        api_response = await k8s_client.list_namespaced_pod(
            namespace, label_selector='release={}'.format(name))
        for api_items in api_response.items:
            pods.append(api_items.metadata.name)
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")

    # Iterate over list of pods and concatenate logs
    logs = ""
    try:
        for pod in pods:
            logs += pod + "\n"
            logs += await k8s_client.read_namespaced_pod_log(
                pod, namespace, tail_lines=tail_lines)
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->read_namespaced_pod_log: {e}")

    return logs


async def _get_pod_logs(pod, namespace, tail_lines=TAIL_LINES_DEFAULT):
    """Read pod logs"""
    k8s_client = client.CoreV1Api()
    ret = []
    try:
        ret = await k8s_client.read_namespaced_pod_log(
            pod, namespace, tail_lines=tail_lines)
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")

    return ret


async def _describe_pod(pod, namespace):
    """Describes pod"""
    k8s_client = client.CoreV1Api()

    try:
        ret = await k8s_client.read_namespaced_pod(
            pod, namespace, pretty='true')
    except ApiException as e:
        logging.exception(
            f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")
        ret = {}
    return ret


async def _get_pod_events(pod, namespace):
    """Get pod events"""
    k8s_client = client.CoreV1Api()
    events = {}

    try:
        ret_events = await k8s_client.list_namespaced_event(
            field_selector=f"involvedObject.name={pod}",
            namespace=namespace)
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->list_namespaced_event: {e}")

    logging.debug(f"found events: {ret_events.items}")
    for counter, event in enumerate(ret_events.items):
        events[counter] = dict(
                Type=event.type,
                Reason=event.reason,
                From=event.reporting_component,
                Age=event.last_timestamp,
                Message=event.message)

    return events


async def _get_all_namespaces():
    """Get all namespaces"""
    k8s_client = client.CoreV1Api()
    namespaces = []

    ret = await k8s_client.list_namespace(watch=False)
    for i in ret.items:
        namespaces.append(i.metadata.name)

    return namespaces


async def _get_all_pods(namespace=None):
    """Get all pods"""
    pods = {}
    k8s_client = client.CoreV1Api()

    if namespace:
        ret = await k8s_client.list_namespaced_pod(namespace, watch=False)
    else:
        ret = await k8s_client.list_pod_for_all_namespaces(watch=False)

    for i in ret.items:
        pod = i.metadata.name
        namespace = i.metadata.namespace
        pods.update({pod: i.metadata.namespace})

    return pods


def _gather_dns_A_info(domain, nameserver):
    dns_info_A = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.A, nameserver=nameserver)
    return dns_info_A.dns_query()


def _gather_dns_NS_info(domain, nameserver):
    dns_info_NS = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.NS, nameserver=nameserver)
    return dns_info_NS.dns_query()


def _gather_dns_MX_info(domain, nameserver):
    dns_info_MX = dinghy_dns.DinghyDNS(
        domain, rdata_type=dns.rdatatype.MX, nameserver=nameserver)
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
        datadog.statsd.increment('dinghy_ping_http_connection_check.increment',
                                 tags=dd_tags)
        r = requests.get(
            f'{protocol}://{domain}',
            params=params, timeout=5, headers=headers)
    except requests.exceptions.Timeout as err:
        domain_response_text = f'Timeout: {err}'
        # Count how many times a user requests a TCP check
        datadog.statsd.increment(
            'dinghy_ping_event_http_connection_check_fail_timeout.increment',
            tags=dd_tags)
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )
    except requests.exceptions.TooManyRedirects as err:
        domain_response_text = f'TooManyRedirects: {err}'
        # Count how many times a user gets TooManyRedirect response
        datadog.statsd.increment(
            'dinghy_ping_event_http_connection_check_fail_redirects.increment',
            tags=dd_tags)
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )
    except requests.exceptions.RequestException as err:
        domain_response_text = f'RequestException: {err}'
        # Count how many times a user get a request exception with their check
        datadog.statsd.increment(
            'dinghy_ping_event_http_connection_check_fail_exception.increment',
            tags=dd_tags)
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_headers = dict(r.headers)
    domain_response_time_ms = r.elapsed.microseconds / 1000

    d = DinghyData(
        redis_host, domain_response_code,
        domain_response_time_ms, r.url)
    d.save_ping()

    return (
        domain_response_code, domain_response_text,
        domain_response_time_ms, domain_response_headers
    )


def _get_all_pinged_urls():
    """Get pinged URLs from Dinghy-ping data module"""
    p = DinghyData(redis_host)

    return p.get_all_pinged_urls()


if __name__ == '__main__':
    initialize_datadog()
    config.load_incluster_config()
    port = int(os.environ.get("DINGHY_LISTEN_PORT", 80))
    debug = os.environ.get("DEBUG", True)
    api.run(address="0.0.0.0", port=port, debug=debug)
