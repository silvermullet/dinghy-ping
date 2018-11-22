### Dinghy Ping

[![Build Status](https://travis-ci.org/silvermullet/dinghy-ping.svg?branch=master)](https://travis-ci.org/silvermullet/dinghy-ping)

![dinghy](https://user-images.githubusercontent.com/538171/47242041-7d96d600-d3a2-11e8-8c55-a04e1249bc46.jpeg)

Dinghy Ping is a simple network debugging interface meant to be deployed into your compute infrastructure (ie, Kubernetes). Used for debugging network connectivity to other services local to Dinghy Ping or external to the compute infrastructure (egress). Meant to answer simple connectivity questions developers might have when deploying their applications to a container orchestration setup where routing and accessibility may be different from their local development environments.

<img width="469" alt="screen shot 2018-11-15 at 11 16 05 pm" src="https://user-images.githubusercontent.com/538171/48603798-82609280-e92c-11e8-9bb0-9b683bb08da8.png"> <img width="822" alt="screen shot 2018-11-13 at 10 11 15 pm" src="https://user-images.githubusercontent.com/538171/48463557-4d6c0880-e791-11e8-9c31-4555c6282a21.png">

#### Docker Run as Daemon

```
docker run -p 80:80 -d sepulworld/dinghy-ping:latest
```

#### Requirements

```pipenv install```

#### Localhost

```python3 api.py```

#### Local Docker Build

```bash
docker build . --tag dinghy:latest
docker run -p 80:80 dinghy:latest
```

#### Dinghy ping single endpoint

```bash
curl "http://127.0.0.1/dinghy/ping/https/google.com"
```

#### Dinghy ping single endpoint with params

```bash
curl "http://127.0.0.1/dinghy/ping/https/www.google.com/search?source=hp&ei=aIHTW9mLNuOJ0gK8g624Ag&q=dinghy&btnK=Google+Search&oq=dinghy&gs_l=psy-ab.3..35i39l2j0i131j0i20i264j0j0i20i264j0l4.4754.5606..6143...1.0..0.585.957.6j5-1......0....1..gws-wiz.....6..0i67j0i131i20i264.oe0qJ9brs-8"
```

#### Dinghy ping multiple sites

```bash
# dinghy-ping multiple sites
curl -vX POST "http://127.0.0.1/dinghy/ping/domains" \
  -d @tests/multiple_domains.json \
  --header "Content-Type: application/json"
```

#### Helm Install

```
helm install -n dinghy-ping ./helm/dinghy-ping
```

#### Local development on Mac with Docker controlled K8s

##### Install Docker for MacOS and enable Kubernetes

```
# Install ingress-nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/mandatory.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/provider/cloud-generic.yaml
```

##### Update your /etc/hosts
```
127.0.0.1 localhost dinghy-ping.localhost
```

##### Install dinghy-ping helm chart, modify to docker image tag of your branch, pr, or release tag
```
helm upgrade --install dinghy-ping ./helm/dinghy-ping/ --set image.tag=v0.0.9 --set ingress.subdomain="localhost"
```

##### Navigate to Dinghy-Ping in browser
http://dinghy-ping.localhost

