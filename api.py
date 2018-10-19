import responder
import requests

api = responder.API()

# Todo make this a landing page, perhaps with an input text box to add domains to request responses from
@api.route("/dinghy")
def dinghy_html(req, resp):
    resp.content = api.template('ping_input.html')

@api.route("/dinghy/ping/{protocol}/{domain}")
def domain_response_html(req, resp, *, protocol, domain):
    r = requests.get(f'{protocol}://{domain}')

    domain_response_code = r.status_code
    domain_response_text = r.text
    resp.content = api.template(
            'ping_response.html',
            domain=domain,
            domain_response_code=domain_response_code, 
            domain_response_text=domain_response_text
    )

if __name__ == '__main__':
    api.run(address="0.0.0.0")
