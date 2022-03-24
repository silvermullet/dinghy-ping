FROM kennethreitz/pipenv

ENV DD_SERVICE_NAME="dinghy-ping"
ENV DD_AGENT_HOST=localhost
ENV DD_DOGSTATSD_SOCKET=""

EXPOSE 80/tcp 8000/tcp

COPY . /app
ENV PYTHONPATH=/app/
CMD ddtrace-run python3 /app/dinghy_ping/services/api.py
