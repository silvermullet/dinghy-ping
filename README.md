### Dinghy Ping

![dinghy](https://user-images.githubusercontent.com/538171/47242041-7d96d600-d3a2-11e8-8c55-a04e1249bc46.jpeg)

#### Requirements

```pipenv install```

#### Localhost

```python3 api.py```


#### Docker

```
docker build . --tag dinghy:latest
docker run -p 80:80 dinghy:latest
curl http://127.0.0.1:5042/dinghy/ping/https/google.com
```
