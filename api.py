import responder
import requests
import asyncio
import os
import data
from urllib.parse import urlparse

api = responder.API(title="Dinghy Ping", version="1.0", openapi="3.0.0", docs_route="/docs")

# For local mac docker image creation and testing, switch to host.docker.internal
redis_host = os.getenv("REDIS_HOST", default="127.0.0.1")


@api.route("/")
def dinghy_html(req, resp):
    resp.content = api.template(
        'ping_input.html',
        get_all_pinged_urls=_get_all_pinged_urls()
    )


@api.route("/dinghy/ping/domains")
async def ping_multiple_domains(req, resp):
    """
    Async process to test multiple domains and return JSON with results
    Post request data example
    {
      "domains": [
        {
          "protocol": "https",
          "domain": "google.com"
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

    results = []

    def build_domain_results(protocol, request_domain, results):
        domain_response_code, domain_response_text, domain_response_time_ms = _process_request(protocol, request_domain, req.params)
        results.append({
            "protocol": protocol,
            "domain": request_domain,
            "domain_response_code": domain_response_code,
            "domain_response_time_ms": domain_response_time_ms
        })

    def gather_results(data):
        for domain in data['domains']:
            protocol = domain['protocol']
            request_domain = domain['domain']
            build_domain_results(protocol, request_domain, results)

    resp.media = {"domains_response_results": results, "wait": gather_results(await req.media())}


@api.route("/dinghy/ping/{protocol}/{domain}")
def domain_response_html(req, resp, *, protocol, domain):
    """
    API endpoint for sending a request to a domain via user specified protocol
    response containts status_code, body text and response_time_ms
    """

    domain_response_code, domain_response_text, domain_response_time_ms = _process_request(protocol, domain, req.params)

    resp.content = api.template(
            'ping_response.html',
            domain=domain,
            domain_response_code=domain_response_code,
            domain_response_text=domain_response_text,
            domain_response_time_ms=domain_response_time_ms
    )


@api.route("/dinghy/form-input")
def form_input(req, resp):
    url = urlparse(req.params['url'])
    if url.scheme == "":
        scheme_notes = "Scheme not given, defaulting to https"
    else:
        scheme_notes = f'Scheme {url.scheme} provided'

    domain_response_code, domain_response_text, domain_response_time_ms = _process_request(url.scheme, url.netloc + url.path, url.query)

    resp.content = api.template(
            'ping_response.html',
            request=f'{req.params["url"]}',
            scheme_notes=scheme_notes,
            domain_response_code=domain_response_code,
            domain_response_text=domain_response_text,
            domain_response_time_ms=domain_response_time_ms
    )


def _process_request(protocol, domain, params):
    """
    Internal method to run request process, takes protocol and domain for input
    """

    if protocol == "":
        protocol = "https"

    domain_response_code = ""
    domain_response_text = ""
    domain_response_time_ms = ""

    try:
        r = requests.get(f'{protocol}://{domain}', params=params, timeout=5)
    except requests.exceptions.Timeout as err:
        domain_response_text = f'Timeout: {err}'
        return domain_response_code, domain_response_text, domain_response_time_ms
    except requests.exceptions.TooManyRedirects as err:
        domain_response_text = f'TooManyRedirects: {err}'
        return domain_response_code, domain_response_text, domain_response_time_ms
    except requests.exceptions.RequestException as err:
        domain_response_text = f'RequestException: {err}'
        return domain_response_code, domain_response_text, domain_response_time_ms

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_time_ms = r.elapsed.microseconds / 1000

    d = data.DinghyData(redis_host, domain_response_code, domain_response_time_ms, r.url)
    d.save_ping()

    return domain_response_code, domain_response_text, domain_response_time_ms

def _get_all_pinged_urls():
    p = data.DinghyData(redis_host)

    return p.get_all_pinged_urls()

if __name__ == '__main__':
    api.run(address="0.0.0.0", port=80, debug=True)
