FROM kennethreitz/pipenv

EXPOSE 80/tcp 8000/tcp

COPY . /app

CMD python3 /app/dinghy_ping/services/api.py
