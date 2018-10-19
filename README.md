### Dinghy Ping from 1999 fast foword to K8s

#### Requirements

```pipenv install```

#### Localhost

```python3 api.py```


#### Docker

```
docker build . --tag dinghy:latest
docker run -p 5042:5042 dinghy:latest
curl http://127.0.0.1:5042/dinghy/ping/https/google.com
```
