### Dinghy Ping

[![Build Status](https://travis-ci.org/silvermullet/dinghy-ping.svg?branch=master)](https://travis-ci.org/silvermullet/dinghy-ping)

![dinghy](https://user-images.githubusercontent.com/538171/47242041-7d96d600-d3a2-11e8-8c55-a04e1249bc46.jpeg) 

Dinghy Ping is a simple network debugging interface meant to be deployed into your compute infrastructure (ie, Kubernetes). Used for debugging network connectivity to other services local to Dinghy Ping or external to the compute infrastructure (egress). Meant to answer simple connectivity questions developers might have when deploying their applications to a container orchestration setup where routing and accessibility may be different from their local development environments.

<img width="906" alt="dinghy ping input" src="https://user-images.githubusercontent.com/538171/51016402-1c0b8100-1525-11e9-81f4-23bb3ef1f687.png">

#### Display for response headers
<img width="948" alt="Screen Shot 2019-07-25 at 11 05 32 AM" src="https://user-images.githubusercontent.com/538171/61897586-3bb83480-aecc-11e9-9fcb-2c379e5f23bb.png">

#### Formated display for response body
<img width="1127" alt="Screen Shot 2019-07-25 at 11 07 28 AM" src="https://user-images.githubusercontent.com/538171/61897679-6e622d00-aecc-11e9-881f-0219f3832d1b.png">

#### Pod logs, per namespace
<img width="984" alt="Screen Shot 2019-07-25 at 11 01 50 AM" src="https://user-images.githubusercontent.com/538171/61897763-9ce00800-aecc-11e9-9312-1bddd4677203.png">

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

#### Deployment pod logs API
```bash
# 1000 line truncated response
curl "https://127.0.0.1/deployment-logs/kube-addons/dinghy-ping?json=true?preview=true"
```

```bash
# Full logs 
curl "https://127.0.0.1/deployment-logs/kube-addons/dinghy-ping?json=true"
```

#### Local development on Mac with Docker controlled K8s

##### Install Docker for MacOS and enable Kubernetes

* requires Docker for Mac 2.x or greater
* Enable Kubernetes on Docker for Mac under preferences

```
# Install ingress-nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/mandatory.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/cloud-generic.yaml
```

##### Update your /etc/hosts
```
127.0.0.1 localhost dinghy-ping.localhost
```

##### Install dinghy-ping helm chart, modify to docker image tag of your branch, pr, or release tag
```
# Init helm if your local k8s doesn't have it yet
helm init
helm repo add dinghy-ping https://sepulworld.github.io/dinghy-ping-helm-chart/
helm upgrade --install dinghy-ping dinghy-ping/dinghy-ping --set image.tag=v0.3.2 --set ingress.subdomain="localhost" --namespace default
```

##### Run tests
```
pytest tests/
```

##### Navigate to Dinghy-Ping in browser
http://dinghy-ping.localhost

![dinghy copy](https://user-images.githubusercontent.com/538171/50532052-77228a00-0ac8-11e9-8ffd-12f53f55724e.png)
