import responder
import requests

api = responder.API()

@api.route("/dinghy")
def dinghy_html(req, resp):
    resp.content = api.template('ping_input.html')

@api.route("/dinghy/ping/{protocol}/{domain}")
def domain_response_html(req, resp, *, protocol, domain):
    """
    API endpoint for sending a request to a domain via user specified protocol
    response containts status_code, body text and response_time_ms
    """
    r = requests.get(f'{protocol}://{domain}')

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_time_ms = r.elapsed.microseconds / 1000

    resp.content = api.template(
            'ping_response.html',
            domain=domain,
            domain_response_code=domain_response_code,
            domain_response_text=domain_response_text,
            domain_response_time_ms=domain_response_time_ms
    )

if __name__ == '__main__':
    api.run(address="0.0.0.0", port=80)
