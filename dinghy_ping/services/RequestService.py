from prometheus_client import Counter, Summary
import dinghy_ping.models.data as data
import requests

class RequestService:
  def __init__(self, redis_host):
      self.redis_host = redis_host

  # Prometheus metrics
  COMPLETED_REQUEST_COUNTER = Counter('dingy_pings_completed', 'Count of completed dinghy ping requests')
  FAILED_REQUEST_COUNTER = Counter('dingy_pings_failed', 'Count of failed dinghy ping requests')
  REQUEST_TIME = Summary('dinghy_request_processing_seconds', 'Time spent processing request')

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
          self.COMPLETED_REQUEST_COUNTER.inc()
      except requests.exceptions.Timeout as err:
          domain_response_text = f'Timeout: {err}'
          self.FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers
      except requests.exceptions.TooManyRedirects as err:
          domain_response_text = f'TooManyRedirects: {err}'
          self.FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers
      except requests.exceptions.RequestException as err:
          domain_response_text = f'RequestException: {err}'
          self.FAILED_REQUEST_COUNTER.inc()
          return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers

      domain_response_code = r.status_code
      domain_response_text = r.text
      domain_response_headers = dict(r.headers)
      domain_response_time_ms = r.elapsed.microseconds / 1000
      print(domain_response_headers)

      d = data.DinghyData(self.redis_host, domain_response_code, domain_response_time_ms, r.url)
      d.save_ping()

      return domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers