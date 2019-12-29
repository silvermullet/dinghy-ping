import responder
import requests
from prometheus_client import Counter, Summary, start_http_server
import asyncio
import os
import json
import sys
import dns.rdatatype
import logging
import traceback
from urllib.parse import urlparse
from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.rest import ApiException
sys.path.insert(0, './dinghy_ping/models/')
import data # noqa
import dinghy_dns # noqa


logging.basicConfig(level=logging.DEBUG)

# Prometheus metrics
COMPLETED_REQUEST_COUNTER = Counter(
    'dingy_pings_completed', 'Count of completed dinghy ping requests'
    )
FAILED_REQUEST_COUNTER = Counter(
    'dingy_pings_failed', 'Count of failed dinghy ping requests'
    )
REQUEST_TIME = Summary(
    'dinghy_request_processing_seconds', 'Time spent processing request'
    )

TAIL_LINES_DEFAULT = 100
LOGS_PREVIEW_LENGTH = 1000
TEMPLATE_DIR = 'dinghy_ping/views/templates/'
STATIC_DIR = 'dinghy_ping/views/static/'


def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))


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
dinghy_ping_host = os.getenv(
    "DINGHY_PING_HOST", default="dinghy-ping.localhost")


@api.route("/")
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
        d = data.DinghyData(
            redis_host,
            domain_response_code=None,
            domain_response_time_ms=None,
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
async def form_input_dns_info(req, resp):
    """Form input endpoint for dns info"""
    domain = req.params['domain']

    if 'nameserver' in req.params.keys():
        nameserver = req.params['nameserver']
    else:
        nameserver = None

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


@api.route("/list-pods")
async def list_pods(req, resp):
    """Route to list pods"""
    namespace = req.params['namespace']

    try:
        ret = await _get_all_pods(namespace)
    except Exception:
        traceback.print_exc(file=sys.stdout)

    resp.media = {"pods": ret}


@api.route("/get/pods")
async def dinghy_get_pods(req, resp):
    """Form input page for pod logs and describe, input namespace"""

    resp.content = api.template(
        'pods_tabbed.html',
        namespaces=await _get_all_namespaces()
    )


@api.route("/get/pod-details")
async def dinghy_get_pod_details(
        req, resp, namespace="default", tail_lines=TAIL_LINES_DEFAULT):
    """Landing page for Dinghy-ping pod logs input html form"""
    if 'namespace' in req.params:
        namespace = req.params['namespace']

    if 'tail_lines' in req.params:
        tail_lines = req.params['tail_lines']

    resp.content = api.template(
        'pod_logs_input.html',
        all_pods=await _get_all_pods(namespace=namespace),
        tail_lines=tail_lines
    )


@api.route("/input-pod-logs")
async def form_input_pod_logs(req, resp, *, tail_lines=TAIL_LINES_DEFAULT):
    """List pods in namespace and click on one to display logs"""
    pod = req.params['pod']
    namespace = req.params['namespace']
    tail_lines = req.params['tail_lines']

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


@api.route("/ws/logstream", websocket=True)
async def log_stream_websocket(ws):
    config.load_incluster_config()
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


@api.route("/pod-describe")
async def dinghy_pod_describe(req, resp):
    """Describe given pod and display response"""
    pod = req.params['pod']
    namespace = req.params['namespace']

    resp.content = api.template(
        'pod_describe_output.html',
        described=await _describe_pod(pod, namespace),
        pod=pod,
        namespace=namespace
    )


@api.route("/deployment-logs/{namespace}/{name}")
async def dinghy_deployment_logs(
                            req, resp, *,
                            namespace, name,
                            tail_lines=TAIL_LINES_DEFAULT,
                            preview=LOGS_PREVIEW_LENGTH):
    """Get pod logs for a given deployment"""
    if 'tail_lines' in req.params.keys():
        tail_lines = req.params['tail_lines']
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
    config.load_incluster_config()
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
    config.load_incluster_config()
    k8s_client = client.CoreV1Api()

    try:
        ret = await k8s_client.read_namespaced_pod_log(
            pod, namespace, tail_lines=tail_lines)
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")

    return ret


async def _describe_pod(pod, namespace):
    """Describes pod"""
    config.load_incluster_config()
    k8s_client = client.CoreV1Api()

    try:
        ret = await k8s_client.read_namespaced_pod(
            pod, namespace, pretty='true')
    except ApiException as e:
        logging.error(
            f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")

    return ret


async def _get_all_namespaces():
    """Get all namespaces"""
    config.load_incluster_config()
    k8s_client = client.CoreV1Api()
    namespaces = []

    ret = await k8s_client.list_namespace(watch=False)
    for i in ret.items:
        namespaces.append(i.metadata.name)

    return namespaces


async def _get_all_pods(namespace=None):
    """Get all pods"""
    pods = {}
    config.load_incluster_config()
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


@REQUEST_TIME.time()
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
        r = requests.get(
            f'{protocol}://{domain}',
            params=params, timeout=5, headers=headers)
        COMPLETED_REQUEST_COUNTER.inc()
    except requests.exceptions.Timeout as err:
        domain_response_text = f'Timeout: {err}'
        FAILED_REQUEST_COUNTER.inc()
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )
    except requests.exceptions.TooManyRedirects as err:
        domain_response_text = f'TooManyRedirects: {err}'
        FAILED_REQUEST_COUNTER.inc()
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )
    except requests.exceptions.RequestException as err:
        domain_response_text = f'RequestException: {err}'
        FAILED_REQUEST_COUNTER.inc()
        return (
            domain_response_code, domain_response_text,
            domain_response_time_ms, domain_response_headers
        )

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_headers = dict(r.headers)
    domain_response_time_ms = r.elapsed.microseconds / 1000

    d = data.DinghyData(
        redis_host, domain_response_code, domain_response_time_ms, r.url)
    d.save_ping()

    return (
        domain_response_code, domain_response_text,
        domain_response_time_ms, domain_response_headers
    )


def _get_all_pinged_urls():
    """Get pinged URLs from Dinghy-ping data module"""
    p = data.DinghyData(redis_host)

    return p.get_all_pinged_urls()


if __name__ == '__main__':
    start_http_server(8000)
    api.run(address="0.0.0.0", port=80, debug=True)
