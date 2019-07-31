from kubernetes.client.rest import ApiException
import logging
from urllib.parse import urlparse
import json
import requests # needed for process request which is temporary

api = None

class HttpController:

  def __init__(self, api, k8s_client):
    self.k8s_client = k8s_client
    global api
    self.api = api
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
          _process_request(url.scheme, url.netloc + url.path, url.query, headers)
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

  
  @REQUEST_TIME.time()
  def _process_request(self, protocol, domain, params, headers):
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
          r = requests.get(f'{protocol}://{domain}', params=params, timeout=5, headers=headers)
          COMPLETED_REQUEST_COUNTER.inc()
      except requests.exceptions.Timeout as err:
          domain_response_text = f'Timeout: {err}'
          FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers
      except requests.exceptions.TooManyRedirects as err:
          domain_response_text = f'TooManyRedirects: {err}'
          FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers
      except requests.exceptions.RequestException as err:
          domain_response_text = f'RequestException: {err}'
          FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers

      domain_response_code = r.status_code
      domain_response_text = r.text
      domain_response_headers = dict(r.headers)
      domain_response_time_ms = r.elapsed.microseconds / 1000
      print(domain_response_headers)

      d = data.DinghyData(self.redis_host, domain_response_code, domain_response_time_ms, r.url)
      d.save_ping()

      return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers