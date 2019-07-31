from kubernetes.client.rest import ApiException
from dinghy_ping.services.LogService import LogService
import logging

api = None

class LogController:

  NUMBER_DEFAULT_TAIL_LINES = 100
  LOGS_PREVIEW_LENGTH = 1000

  def __init__(self, api, k8s_client):
      self.log_service = LogService(k8s_client)
      global api
      api = api
  
  @api.route("/get/pod-logs")
  def dinghy_get_pod_logs(self, req, resp):
      """Form input page for pod logs, input namespace"""
      resp.content = api.template(
          'pod_logs.html'
      )


  @api.route("/post/pod-logs")
  def dinghy_post_pod_logs(self, req, resp, namespace="default", tail_lines=NUMBER_DEFAULT_TAIL_LINES):
      """Landing page for Dinghy-ping pod logs input html form"""
      if 'namespace' in req.params.keys():
          namespace = req.params['namespace']

      if 'tail_lines' in req.params.keys():
          tail_lines = req.params['tail_lines']

      resp.content = api.template(
          'pod_logs_input.html',
          all_pods=self.log_service._get_all_pods(namespace=namespace),
          tail_lines=tail_lines
      )


  @api.route("/input-pod-logs")
  def form_input_pod_logs(self, req, resp, *, tail_lines=NUMBER_DEFAULT_TAIL_LINES):
      """List pods in namespace and click on one to display logs"""
      pod = req.params['pod']
      namespace = req.params['namespace']
      tail_lines = req.params['tail_lines']

      logs = self.log_service._get_pod_logs(pod, namespace, tail_lines)

      resp.content = api.template(
          'pod_logs_output.html',
          logs=logs
      )

  @api.route("/list-pods")
  def list_pods(self, req, resp):
      """Route to list pods"""
      namespace = req.params['namespace']
      return self.log_service._get_all_pods(namespace)
      
  @api.route("/deployment-logs/{namespace}/{name}")
  def dinghy_deployment_logs(self, req, resp, *, 
                            namespace, name,
                            tail_lines=NUMBER_DEFAULT_TAIL_LINES,
                            preview=LOGS_PREVIEW_LENGTH):
      """Get pod logs for a given deployment"""
      if 'tail_lines' in req.params.keys():
          tail_lines = req.params['tail_lines']
      logs = self.log_service._get_deployment_logs(namespace, name, tail_lines)
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

  
