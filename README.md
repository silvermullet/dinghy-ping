### Dinghy Ping

[![Build Status](https://travis-ci.org/silvermullet/dinghy-ping.svg?branch=master)](https://travis-ci.org/silvermullet/dinghy-ping)

![dinghy](https://user-images.githubusercontent.com/538171/47242041-7d96d600-d3a2-11e8-8c55-a04e1249bc46.jpeg) 

Dinghy Ping is a simple network debugging interface meant to be deployed into your compute infrastructure (ie, Kubernetes). Used for debugging network connectivity to other services local to Dinghy Ping or external to the compute infrastructure (egress). Meant to answer simple connectivity questions developers might have when deploying their applications to a container orchestration setup where routing and accessibility may be different from their local development environments.

<img width="906" alt="dinghy ping input" src="https://user-images.githubusercontent.com/538171/51016402-1c0b8100-1525-11e9-81f4-23bb3ef1f687.png">

##### Helm Install

[Helm](https://helm.sh) must be installed to use the charts.  Please refer to
Helm's [documentation](https://helm.sh/docs) to get started.

Once Helm has been set up correctly, add the repo as follows:

  helm repo add dinghy-ping https://silvermullet.github.io/dinghy-ping

If you had already added this repo earlier, run `helm repo update` to retrieve
the latest versions of the packages.  You can then run `helm search repo
dinghy-ping` to see the charts.

To install the dinghy-ping chart:

    helm install my-dinghy-ping dinghy-ping/dinghy-ping

To uninstall the chart:

    helm delete my-dinghy-ping

#### Requirements 

 * If using a LoadBalancer with your ingress, there may be some configuration requirements to support web sockets. For example, an AWS ELB must be using "tcp" for backend request.
   See this for more details as to why: https://github.com/kubernetes/ingress-nginx/issues/3746

#### Display for response headers
<img width="948" alt="Screen Shot 2019-07-25 at 11 05 32 AM" src="https://user-images.githubusercontent.com/538171/61897586-3bb83480-aecc-11e9-9fcb-2c379e5f23bb.png">

#### Formated display for response body
<img width="1127" alt="Screen Shot 2019-07-25 at 11 07 28 AM" src="https://user-images.githubusercontent.com/538171/61897679-6e622d00-aecc-11e9-881f-0219f3832d1b.png">

#### Streaming Pod logs, per namespace
![dinghy_logs_streaming_g1](https://user-images.githubusercontent.com/538171/72676471-d09c8480-3a4e-11ea-957f-d656f2db91db.gif)


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
* Install [Tilt](https://docs.tilt.dev/install.html)

#### Tilt

```
tilt up
```
Navigate to http://127.0.0.1:8080/

##### Run tests
```
pytest tests/
```

