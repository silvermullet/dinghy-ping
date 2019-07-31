import dinghy_ping.models.data as data

class PingService:

  def __init__(self, redis_host):
    self.redis_host = redis_host

  def _get_all_pinged_urls(self):
    """Get pinged URLs from Dinghy-ping data module"""
    p = data.DinghyData(self.redis_host)

    return p.get_all_pinged_urls() 

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
