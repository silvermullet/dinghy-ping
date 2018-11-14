import json
import pytest
import sys
sys.path.insert(0, './')
import api as service


with open('tests/multiple_domains.json') as f:
    multiple_domains = json.load(f)


@pytest.fixture
def api():
    return service.api


@pytest.fixture
def session(api):
    return api.requests


def test_dinghy_ping_google_http(api):
    r = api.requests.get("/dinghy/ping/http/google.com")
    assert r.status_code == 200


def test_dinghy_ping_google_https_and_query_params(api):
    r = api.requests.get("/dinghy/ping/https/www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8")
    assert r.status_code == 200


def test_dinghy_ping_google_no_proto_set_and_query_params(api):
    r = api.requests.get("/dinghy/ping//www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8")
    assert r.status_code == 200


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