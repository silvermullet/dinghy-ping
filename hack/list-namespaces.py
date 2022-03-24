from __future__ import print_function
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pprint import pprint

config.load_kube_config()
k8s_client = client.CoreV1Api()
pretty = 'true' # str | If 'true', then the output is pretty printed. (optional)

"""
{'api_version': 'v1',
 'items': [{'api_version': None,
            'kind': None,
            'metadata': {'annotations': {'kubectl.kubernetes.io/last-applied-configuration': '{"apiVersion":"v1","kind":"Namespace","metadata":{"annotations":{},"name":"app"}}\n'},
                         'cluster_name': None,
                         'creation_timestamp': datetime.datetime(2019, 11, 14, 23, 52, 49, tzinfo=tzutc()),
                         'deletion_grace_period_seconds': None,
                         'deletion_timestamp': None,
                         'finalizers': None,
                         'generate_name': None,
                         'generation': None,
                         'initializers': None,
                         'labels': None,
                         'managed_fields': None,
                         'name': 'app',
"""

try:
    api_response = k8s_client.list_namespace(pretty=pretty, watch=False)
except ApiException as e:
    print("Exception when calling CoreV1Api->list_namespace: %s\n" % e)

for namespace in api_response.items:
    print(namespace.metadata.name)
