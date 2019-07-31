import json
import pytest
import sys
import os
import responder
# from dinghy_ping.controllers.PingController import PingController
# from dinghy_ping.services.PingService import PingService
sys.path.insert(0,'./dinghy_ping/')
import models.data as data

TITLE = "Dinghy Ping"
VERSION = "1.0"
OPENAPI_VERSION = "3.0.0"
DOCS_ROUTE = "/docs"
TEMPLATE_DIR = 'dinghy_ping/views/templates/'

with open('tests/multiple_domains.json') as f:
    multiple_domains = json.load(f)

@pytest.fixture
def api():
    api = responder.API(title=TITLE, templates_dir=TEMPLATE_DIR, version=VERSION, openapi=OPENAPI_VERSION, docs_route=DOCS_ROUTE)
    return api

@pytest.fixture
def session(api):
    return api.requests


def test_dinghy_ping_google_http(api):
    r = api.requests.get("/ping/http/google.com")
    assert r.status_code == 200


def test_dinghy_ping_google_tcp(api):
    r = api.requests.get("/form-input-tcp-connection-test?tcp-endpoint=google.com&tcp-port=443")
    assert r.status_code == 200


def test_dinghy_ping_google_https_and_query_params(api):
    r = api.requests.get("/ping/https/www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8")
    assert r.status_code == 200


def test_dinghy_ping_google_no_proto_set_and_query_params(api):
    r = api.requests.get("/ping//www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8")
    assert r.status_code == 200

"""
def test_multiple_domains_request_for_google(api):
    r = api.requests.post(api.url_for("ping_multiple_domains"), json=multiple_domains)
    response_json = r.json()
    assert response_json['domains_response_results'][0]['domain_response_code'] == 200


def test_multiple_domains_request_for_google_with_params(api):
    r = api.requests.post(api.url_for("ping_multiple_domains"), json=multiple_domains)
    response_json = r.json()
    assert response_json['domains_response_results'][1]['domain_response_code'] == 200


def test_multiple_domains_request_for_microsoft(api):
    r = api.requests.post(api.url_for("ping_multiple_domains"), json=multiple_domains)
    response_json = r.json()
    assert response_json['domains_response_results'][2]['domain_response_code'] == 200
"""

# def test_ping_saved_results(api):
#     redis_host = os.getenv("REDIS_HOST", default="127.0.0.1")
#     api.requests.get("/ping/http/www.google.com")
#     ping_service = PingService(redis_host)
#     p = ping_service._get_all_pinged_urls()
#     assert "http://www.google.com/" in p 
