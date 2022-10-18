import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32)
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT") or "True"
    REDIS_HOST = (
        os.environ.get("REDIS_HOST") or "dinghy-ping-redis.default.svc.cluster.local"
    )
    ENVIRONMENT = os.environ.get("ENVIRONMENT") or "none"
    TAIL_LINES_DEFAULT = os.environ.get("TAIL_LINES_DEFAULT") or "100"
    LOGS_PREVIEW_LENGTH = os.environ.get("LOGS_PREVIEW_LENGTH") or "1000"
    DD_TRACE_ENABLED = os.environ.get("DD_TRACE_ENABLED") or "False"
    DD_DOGSTATSD_DISABLE = os.environ.get("DD_DOGSTATSD_DISABLE") or None
    DD_TRACE_AGENT_PORT = os.environ.get("DD_TRACE_AGENT_PORT") or "8126"
    DD_AGENT_HOST = os.environ.get("DD_AGENT_HOST") or "host.docker.internal"
    DD_DOGSTATSD_PORT = os.environ.get("DD_DOGSTATSD_PORT") or "8125"
    DD_TRACE_AGENT_HOSTNAME = (
        os.environ.get("DD_TRACE_AGENT_HOSTNAME") or "host.docker.internal"
    )
    MY_APP_NAME = os.environ.get("MY_APP_NAME") or "dinghy-ping"
    MY_CLUSTER_DOMAIN = os.environ.get("MY_CLUSTER_DOMAIN") or "localhost"
    TESTING = os.environ.get("TESTING") or "False"
    # If using Gitlab a user name for the token is needed, Github will only need a token
    GIT_USER = os.environ.get("GIT_USER") or ""
    GIT_TOKEN = os.environ.get("GIT_TOKEN") or ""

    # Celery config
    CELERY_BROKER_URL = f"redis://{REDIS_HOST}:6379"
    CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:6379"
