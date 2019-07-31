from dinghy_ping.services.PingService import PingService
from dinghy_ping.services.RequestService import RequestService
api = None

class PingController:

  def __init__(self, api, redis_host):
    self.request_service = RequestService(redis_host)
    self.ping_service = PingService(redis_host)
    global api
    api = api
   
  @api.route("/")
  def dinghy_html(self, req, resp):
      """Index route to Dinghy-ping input html form"""
      resp.content = api.template(
          'index.html',
          get_all_pinged_urls=self.ping_service._get_all_pinged_urls()
      ) 

  @api.route("/ping/{protocol}/{domain}")
  def domain_response_html(self, req, resp, *, protocol, domain):
      """
      API endpoint for sending a request to a domain via user specified protocol
      response containts status_code, body text and response_time_ms
      """

      headers = {}
      domain_response_code, domain_response_text, domain_response_time_ms, domain_response_headers = (
          self.request_service._process_request(protocol, domain, req.params, headers)
      )

      resp.content = api.template(
              'ping_response.html',
              domain=domain,
              domain_response_code=domain_response_code,
              domain_response_text=domain_response_text,
              domain_response_headers=domain_response_headers,
              domain_response_time_ms=domain_response_time_ms
      )
    
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