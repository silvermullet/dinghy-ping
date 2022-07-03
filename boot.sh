#!/bin/bash
exec ddtrace-run gunicorn --worker-tmp-dir /dev/shm --preload -w 3 --timeout 200 -b 0.0.0.0:80 -b 0.0.0.0:8080 --access-logfile - --error-logfile - --log-level info dinghyping:app
