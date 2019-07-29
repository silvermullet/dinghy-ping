import os
import responder
import json
from kubernetes import client, config


TEMPLATE_DIR = 'dinghy_ping/views/templates/'
TITLE = "Dinghy Ping"
VERSION = "1.0"
OPENAPI_VERSION = "3.0.0"
DOCS_ROUTE = "/docs"

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
