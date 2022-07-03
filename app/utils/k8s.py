import logging

from kubernetes import client
from kubernetes.client.rest import ApiException


def get_deployment_logs(namespace, name, tail_lines):
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


def get_pod_logs(pod, namespace, container, tail_lines):
    """Read pod logs"""
    k8s_client = client.CoreV1Api()
    ret = []
    if container:
        try:
            ret = k8s_client.read_namespaced_pod_log(
                pod, namespace, container=container, tail_lines=tail_lines
            )
        except ApiException as e:
            logging.error(
                f"Exception when calling CoreV1Api->read_namespaced_pod_log: {e}"
            )
    else:
        try:
            ret = k8s_client.read_namespaced_pod_log(
                pod, namespace, tail_lines=tail_lines
            )
        except ApiException as e:
            logging.error(
                f"Exception when calling CoreV1Api->read_namespaced_pod_log: {e}"
            )

    return ret


def describe_pod(pod, namespace):
    """Describes pod"""
    k8s_client = client.CoreV1Api()

    try:
        ret = k8s_client.read_namespaced_pod(pod, namespace, pretty="true")
    except ApiException as e:
        logging.exception(f"Exception when calling CoreV1Api->read_namespaced_pod: {e}")
        ret = {}
    return ret


def get_pod_events(pod, namespace):
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


def get_all_namespaces():
    """Get all namespaces"""
    k8s_client = client.CoreV1Api()
    namespaces = []

    ret = k8s_client.list_namespace(watch=False)
    for i in ret.items:
        namespaces.append(i.metadata.name)

    return namespaces


def get_all_pods(namespace=None):
    """Get all pods and return dict of pods with their containers and their namespaces"""
    pods = {}
    k8s_client = client.CoreV1Api()

    if namespace:
        ret = k8s_client.list_namespaced_pod(namespace, watch=False)
    else:
        ret = k8s_client.list_pod_for_all_namespaces(watch=False)

    for i in ret.items:
        pod = i.metadata.name
        namespace = i.metadata.namespace
        containers = []
        for container in i.spec.containers:
            containers.append(container.name)
        pods[pod] = dict(namespace=namespace, containers=containers)

    return pods
