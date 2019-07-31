from kubernetes.client.rest import ApiException
import logging

api = None
TAIL_LINES_DEFAULT = 100
LOGS_PREVIEW_LENGTH = 1000

class LogController:
  def __init__(self, api, k8s_client):
    self.k8s_client = k8s_client
    global api
    self.api = api
    api = api
  
  @api.route("/get/pod-logs")
  def dinghy_get_pod_logs(self, req, resp):
      """Form input page for pod logs, input namespace"""
      resp.content = self.api.template(
          'pod_logs.html'
      )


  @api.route("/post/pod-logs")
  def dinghy_post_pod_logs(self, req, resp, namespace="default", tail_lines=TAIL_LINES_DEFAULT):
      """Landing page for Dinghy-ping pod logs input html form"""
      if 'namespace' in req.params.keys():
          namespace = req.params['namespace']

      if 'tail_lines' in req.params.keys():
          tail_lines = req.params['tail_lines']

      resp.content = self.api.template(
          'pod_logs_input.html',
          all_pods=self._get_all_pods(namespace=namespace),
          tail_lines=tail_lines
      )


  @api.route("/input-pod-logs")
  def form_input_pod_logs(self, req, resp, *, tail_lines=TAIL_LINES_DEFAULT):
      """List pods in namespace and click on one to display logs"""
      pod = req.params['pod']
      namespace = req.params['namespace']
      tail_lines = req.params['tail_lines']

      logs = self._get_pod_logs(pod, namespace, tail_lines)

      resp.content = self.api.template(
          'pod_logs_output.html',
          logs=logs
      )

  @api.route("/list-pods")
  def list_pods(self, req, resp):
      """Route to list pods"""
      namespace = req.params['namespace']
      return self._get_all_pods(namespace)
      
  @api.route("/deployment-logs/{namespace}/{name}")
  def dinghy_deployment_logs(self, req, resp, *, 
                            namespace, name,
                            tail_lines=TAIL_LINES_DEFAULT,
                            preview=LOGS_PREVIEW_LENGTH):
      """Get pod logs for a given deployment"""
      if 'tail_lines' in req.params.keys():
          tail_lines = req.params['tail_lines']
      logs = self._get_deployment_logs(namespace, name, tail_lines)
      logs_preview = logs[0:preview]
      

      if 'json' in req.params.keys():
          if 'preview' in req.params.keys():
              resp.media = {"logs": logs_preview}
          else:
              resp.media = {"logs": logs}
      else:
          resp.content = self.api.template(
              'pod_logs_output.html',
              logs=logs
          )

  def _get_deployment_logs(self, namespace, name, tail_lines=TAIL_LINES_DEFAULT):
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

  def _get_pod_logs(self, pod, namespace, tail_lines=TAIL_LINES_DEFAULT):
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
