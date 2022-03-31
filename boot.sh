#!/bin/bash
exec gunicorn --worker-tmp-dir /dev/shm --preload -w 3 --timeout 200 --chdir dinghy_ping/services -b 0.0.0.0:80 -b 0.0.0.0:8080 --access-logfile - --error-logfile - --log-level debug api:api
#exec ddtrace-run gunicorn --chdir dinghy_ping/services --access-logfile - --error-logfile - api:api
