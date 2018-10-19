import responder
import requests

api = responder.API()

@api.route("/dinghy")
def hello_html(req, resp):
    resp.content = api.template('ping_input.html')

@api.route("/dinghy/ping/{domain}")
def hello_html(req, resp, *, domain):
    r = requests.get(f'http://{domain}')

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
