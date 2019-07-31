from kubernetes.client.rest import ApiException
import logging

class LogService:
  def __init__(self, k8s_client):
      self.k8s_client = k8s_client

  def _get_deployment_logs(self, namespace, name, tail_lines):
      """Gather pod names via K8s label selector"""
      pods = []
      try:
          api_response = self.k8s_client.list_namespaced_pod(namespace, label_selector='release={}'.format(name))
          for api_items in api_response.items:
              pods.append(api_items.metadata.name)
      except ApiException as e:
          print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" % e)

      # Iterate over list of pods and concatenate logs
      logs = ""
      try:
          for pod in pods:
              logs += pod + "\n"
              logs += self.k8s_client.read_namespaced_pod_log(pod, namespace, tail_lines=tail_lines)
      except ApiException as e:
          logging.error("Exception when calling CoreV1Api->read_namespaced_pod_log: %s\n" % e)
      return logs

  def _get_pod_logs(self, pod, namespace, tail_lines):
      """Read pod logs"""
      try:
          ret = self.k8s_client.read_namespaced_pod_log(pod, namespace, tail_lines=tail_lines)
      except ApiException as e:
          logging.error("Exception when calling CoreV1Api->read_namespaced_pod_log: %s\n" % e)

      return ret

  def _get_all_pods(self, namespace=None):
      pods = {}
      if namespace:
          ret = self.k8s_client.list_namespaced_pod(namespace, watch=False)
      else:
          ret = self.k8s_client.list_pod_for_all_namespaces(watch=False)

      for i in ret.items:
          pod = i.metadata.name
          namespace = i.metadata.namespace
          pods.update({ pod: i.metadata.namespace} )

      return pods

  def _get_all_namespaces(self):
    namespaces = []
    ret = self.k8s_client.list_namespace(watch=False)
    for i in ret.items:
        namespaces.append(i.metadata.name)

    return namespaces