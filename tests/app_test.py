import json

import pytest

from app import create_app
from config import Config


class TestConfig(Config):
    TESTING = "True"


with open("tests/multiple_domains.json") as f:
    multiple_domains = json.load(f)


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def session(app):
    return app.requests


# @pytest.fixture
# def redis_my(app):
#    redis_my_proc = factories.redis_proc(port=None)
#    redis_my = factories.redisdb('redis_my_proc')
#
#    return redis_my


def test_dinghy_ping_google_http(client):
    r = client.get("/ping/http/google.com")
    assert r.status_code == 200


def test_dinghy_ping_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_dinghy_ping_google_https_and_query_params(client):
    r = client.get(
        "/ping/https/www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8"  # noqa
    )
    assert r.status_code == 200
