from kennethreitz/pipenv

EXPOSE 80/tcp

COPY . /app
CMD python3 api.py
