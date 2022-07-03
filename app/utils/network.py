import json
import logging
import socket
import time
from urllib.parse import urlparse

import datadog
import dns.rdatatype
import requests
from ddtrace import patch

from app.models.dinghy_data import DinghyData
from app.models.dinghy_dns import DinghyDNS

patch(requests=True)
import requests  # noqa


def http_check(url, headers, redis_host):
    """
    Send a request to a url and return response code, body text and response_time_ms
    """
    url = urlparse(url)
    if headers:
        try:
            headers = json.loads(headers)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding headers input: {e}")
            headers = {}
    else:
        headers = {}

    response_code, response_text, response_time_ms, response_headers = process_request(
        url.scheme, url.netloc + url.path, url.query, headers, redis_host
    )

    request_url = f"{url.scheme}://{url.netloc}{url.path}"

    return (
        response_code,
        response_text,
        response_time_ms,
        response_headers,
        request_url,
    )


def tcp_check(tcp_endpoint, tcp_port, redis_host):
    """
    Check tcp endpoint and port, hard timeout at 5 seconds
    """
    deadline = time.time() + 5.0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(deadline - time.time())
            s.connect((tcp_endpoint, tcp_port))
            conn_info = f"Connection created to {tcp_endpoint} on port {tcp_port}"

        d = DinghyData(
            redis_host,
            domain_response_code="tcp handshake success",
            domain_response_time_ms="N/A",
            request_url=f"{tcp_endpoint}:{tcp_port}",
        )
        d.save_ping()
    except Exception as e:
        conn_info = f"Failed to connect to {tcp_endpoint} on port {tcp_port}: {e}"
        d = DinghyData(
            redis_host,
            domain_response_code=f"tcp handshake failed: {e}",
            domain_response_time_ms="N/A",
            request_url=f"{tcp_endpoint}:{tcp_port}",
        )
        d.save_ping()

    return conn_info


def dns_check(domain, nameserver, redis_host):
    """
    Check dns resolution results for a given nameserver and domain
    """

    dns_info_A = _gather_dns_A_info(domain, nameserver)
    dns_info_NS = _gather_dns_NS_info(domain, nameserver)
    dns_info_MX = _gather_dns_MX_info(domain, nameserver)

    d = DinghyData(
        redis_host,
        domain_response_code=f"dns lookup for {domain} on {nameserver}",
        domain_response_time_ms="N/A",
        request_url=domain,
    )
    d.save_ping()

    return dns_info_A, dns_info_NS, dns_info_MX


def process_request(protocol, domain, params, headers, redis_host):
    """
    Internal method to run request process, takes protocol and domain for input
    """

    if protocol == "":
        protocol = "https"

    domain_response_code = ""
    domain_response_text = ""
    domain_response_time_ms = ""
    domain_response_headers = {}

    try:
        # Count how many times a user requests an HTTP check
        datadog.statsd.increment("dinghy_ping_http_connection_check.increment")
        r = requests.get(
            f"{protocol}://{domain}", params=params, timeout=5, headers=headers
        )
    except requests.exceptions.Timeout as err:
        domain_response_text = f"Timeout: {err}"
        # Count how many times a user requests a TCP check
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_timeout.increment"
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )
    except requests.exceptions.TooManyRedirects as err:
        domain_response_text = f"TooManyRedirects: {err}"
        # Count how many times a user gets TooManyRedirect response
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_redirects.increment"
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )
    except requests.exceptions.RequestException as err:
        domain_response_text = f"RequestException: {err}"
        # Count how many times a user get a request exception with their check
        datadog.statsd.increment(
            "dinghy_ping_event_http_connection_check_fail_exception.increment"
        )
        return (
            domain_response_code,
            domain_response_text,
            domain_response_time_ms,
            domain_response_headers,
        )

    domain_response_code = r.status_code
    domain_response_text = r.text
    domain_response_headers = dict(r.headers)
    domain_response_time_ms = r.elapsed.microseconds / 1000

    d = DinghyData(redis_host, domain_response_code, domain_response_time_ms, r.url)
    d.save_ping()

    return (
        domain_response_code,
        domain_response_text,
        domain_response_time_ms,
        domain_response_headers,
    )


def get_all_pinged_urls(redis_host):
    """Get pinged URLs from Dinghy-ping data module"""
    p = DinghyData(redis_host)
    return p.get_all_pinged_urls()


def _gather_dns_A_info(domain, nameserver):
    dns_info_A = DinghyDNS(domain, rdata_type=dns.rdatatype.A, nameserver=nameserver)
    return dns_info_A.dns_query()


def _gather_dns_NS_info(domain, nameserver):
    dns_info_NS = DinghyDNS(domain, rdata_type=dns.rdatatype.NS, nameserver=nameserver)
    return dns_info_NS.dns_query()


def _gather_dns_MX_info(domain, nameserver):
    dns_info_MX = DinghyDNS(domain, rdata_type=dns.rdatatype.MX, nameserver=nameserver)
    return dns_info_MX.dns_query()
