import datetime
import json
import logging
import os
from logging.handlers import RotatingFileHandler

import datadog
from ddtrace import tracer
from flask import Flask
from kubernetes import config
from redis import StrictRedis

from config import Config


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()


def to_pretty_json(value):
    return json.dumps(
        value, sort_keys=True, indent=4, separators=(",", ": "), default=default
    )


def initialize_datadog(dd_tags):
    dd_statsd_port = os.getenv("DD_DOGSTATSD_PORT", "8125")
    dd_trace_agent_hostname = os.getenv(
        "DD_TRACE_AGENT_HOSTNAME", "host.docker.internal"
    )
    dd_host = os.getenv("DD_AGENT_HOST", "host.docker.internal")
    dd_trace_agent_port = os.getenv("DD_TRACE_AGENT_PORT", "8126")
    datadog_options = {"statsd_host": dd_host, "statsd_port": dd_statsd_port}
    if os.getenv("DD_DOGSTATSD_DISABLE") is None:
        datadog.initialize(
            enabled=False,
            statsd_host="localhost",
            statsd_port=8125,
            statsd_prefix="dinghy_ping",
            statsd_tags=dd_tags,
        )
    else:
        datadog.initialize(**datadog_options)

    if os.getenv("DD_TRACE_ENABLED"):
        tracer.configure(
            hostname=dd_trace_agent_hostname,
            port=dd_trace_agent_port,
            service="dinghy_ping",
            tags=dd_tags,
        )
    else:
        tracer.enabled = False


def create_app(config_class=Config):
    # might need static_folder=STATIC_DIR
    app = Flask(__name__, static_folder="templates/static")

    app.config.from_object(config_class)
    app.jinja_env.filters["tojson_pretty"] = to_pretty_json

    # app.redis = Redis.from_url(app.config['REDIS_HOST'])
    app.redis = StrictRedis(host=app.config["REDIS_HOST"])

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.main.ws import sock

    sock.init_app(app)

    if app.config["TESTING"] == "True":
        logging.info("TESTING is True, not loading k8s client")
    else:
        config.load_incluster_config()
    environment = app.config["ENVIRONMENT"]
    dd_tags = [f"environment={environment}"]
    initialize_datadog(dd_tags)

    if app.config["MY_CLUSTER_DOMAIN"] == "localhost":
        # building ws host for localhost Tilt development over http
        app.config["DINGHY_PING_WEB_SOCKET_HOST"] = "ws://localhost:8080"
    else:
        app.config[
            "DINGHY_PING_WEB_SOCKET_HOST"
        ] = f"wss://{app.config['MY_APP_NAME']}.{app.config['MY_CLUSTER_DOMAIN']}:443"

    if not app.debug and not app.testing:
        if app.config["LOG_TO_STDOUT"]:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists("logs"):
                os.mkdir("logs")
            file_handler = RotatingFileHandler(
                "logs/dinghyping.log", maxBytes=10240, backupCount=10
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s "
                    "[in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("DinghyPing startup")

    return app


from app import models  # noqa
