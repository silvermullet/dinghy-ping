import os
import responder
import json
import sys
from kubernetes import client, config
from prometheus_client import start_http_server
sys.path.insert(0, './dinghy_ping/')
from controllers.LogController import LogController
from controllers.TcpController import TcpController
from controllers.DnsController import DnsController
from controllers.HttpController import HttpController
from controllers.PingController import PingController

TITLE = "Dinghy Ping"
VERSION = "1.0"
OPENAPI_VERSION = "3.0.0"
DOCS_ROUTE = "/docs"
TEMPLATE_DIR = 'dinghy_ping/views/templates/'

# Configure kubernetes client
if not "IN_TRAVIS" in os.environ:
    config.load_incluster_config()
    k8s_client = client.CoreV1Api()

def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

api = responder.API(title=TITLE, templates_dir=TEMPLATE_DIR, version=VERSION, openapi=OPENAPI_VERSION, docs_route=DOCS_ROUTE)
api.jinja_env.filters['tojson_pretty'] = to_pretty_json

# For local mac docker image creation and testing, switch to host.docker.internal
redis_host = os.getenv("REDIS_HOST", default="127.0.0.1")

# inject api into class
DnsController(api)
TcpController(api, redis_host)
LogController(api, k8s_client)
PingController(api, redis_host)
HttpController(api, k8s_client, redis_host)


if __name__ == '__main__':
    start_http_server(8000)
    api.run(address="0.0.0.0", port=80, debug=True)