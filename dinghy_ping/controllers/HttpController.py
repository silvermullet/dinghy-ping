from dinghy_ping.services.RequestService import RequestService
from kubernetes.client.rest import ApiException
import logging
from urllib.parse import urlparse
import json
import requests # needed for process request which is temporary

api = None

class HttpController:

  def __init__(self, api, k8s_client, redis_host):
    self.request_service = RequestService(redis_host)
    self.k8s_client = k8s_client
    global api
    api = api

  @api.route("/form-input")
  def form_input(self, req, resp):
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

      domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers = (
          self.request_service._process_request(url.scheme, url.netloc + url.path, url.query, headers)
      )

      resp.content = api.template(
              'ping_response.html',
              request=f'{req.params["url"]}',
              scheme_notes=scheme_notes,
              domain_response_code=domain_response_code,
              domain_response_text=domain_response_text,
              domain_response_headers=domain_response_headers,
              domain_response_time_ms=domain_response_time_ms
      )