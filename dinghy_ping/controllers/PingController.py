import requests
import logging
from urllib.parse import urlparse
import json
from prometheus_client import Counter, Summary
import dinghy_ping.models.data as data

api = None

# Prometheus metrics
COMPLETED_REQUEST_COUNTER = Counter('dingy_pings_completed', 'Count of completed dinghy ping requests')
FAILED_REQUEST_COUNTER = Counter('dingy_pings_failed', 'Count of failed dinghy ping requests')
REQUEST_TIME = Summary('dinghy_request_processing_seconds', 'Time spent processing request')


class PingController:

  def __init__(self, api, redis_host):
    self.redis_host = redis_host
    global api
    self.api = api
    api = api
   
  @api.route("/")
  def dinghy_html(self, req, resp):
      """Index route to Dinghy-ping input html form"""
      resp.content = api.template(
          'index.html',
          get_all_pinged_urls=self._get_all_pinged_urls()
      ) 


  def _get_all_pinged_urls(self):
    """Get pinged URLs from Dinghy-ping data module"""
    p = data.DinghyData(self.redis_host)

    return p.get_all_pinged_urls() 


  @api.route("/ping/{protocol}/{domain}")
  def domain_response_html(self, req, resp, *, protocol, domain):
      """
      API endpoint for sending a request to a domain via user specified protocol
      response containts status_code, body text and response_time_ms
      """

      headers = {}
      domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers = (
          self._process_request(protocol, domain, req.params, headers)
      )

      resp.content = api.template(
              'ping_response.html',
              domain=domain,
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
    
  @api.route("/ping/domains")
  async def ping_multiple_domains(self, req, resp):
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
      # results = []

# def build_domain_results(protocol, request_domain, results, headers):
#     domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers = _process_request(protocol, request_domain, req.params, headers)
#     results.append({
#         "protocol": protocol,
#         "domain": request_domain,
#         "domain_response_code": domain_response_code,
#         "domain_response_headers": domain_response_headers,
#         "domain_response_time_ms": domain_response_time_ms
#     })

# def gather_results(data):
#     for domain in data['domains']:
#         protocol = domain['protocol']
#         request_domain = domain['domain']
#         headers = domain['headers']
#         build_domain_results(protocol, request_domain, results, headers)

# resp.media = {"domains_response_results": results, "wait": gather_results(await req.media())}
