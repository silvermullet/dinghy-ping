### Dinghy Ping

[![Build Status](https://travis-ci.org/silvermullet/dinghy-ping.svg?branch=master)](https://travis-ci.org/silvermullet/dinghy-ping)

![dinghy](https://user-images.githubusercontent.com/538171/47242041-7d96d600-d3a2-11e8-8c55-a04e1249bc46.jpeg)

#### Docker Run as Daemon

```
docker run -p 80:80 -d sepulworld/dinghy-ping:latest
```

#### Requirements

```pipenv install```

#### Localhost

```python3 api.py```

#### Local Docker Build 

```
docker build . --tag dinghy:latest
docker run -p 80:80 dinghy:latest

# dinghy-ping a single endpoint
curl http://127.0.0.1/dinghy/ping/https/google.com

# dinghy-ping multiple sites
curl -vX POST "http://127.0.0.1/dinghy/ping/domains" -d @tests/multiple_domains.json --header "Content-Type: application/json"
```
