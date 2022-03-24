#!/bin/bash

set -e

VER=$1
DOCKER_REPO=$2
DOCKER_IMAGE_NAME=$3

kubectx docker-desktop

echo "start image build..."
docker build . --tag "${DOCKER_REPO}"/"${DOCKER_IMAGE_NAME}":dinghy_test_${VER}
echo "done building..."

echo "start docker push"
echo "docker push "${DOCKER_REPO}"/"${DOCKER_IMAGE_NAME}":dinghy_test_${VER}"
docker push "${DOCKER_REPO}"/"${DOCKER_IMAGE_NAME}":dinghy_test_${VER}

echo "Helm install new dinghy-ping image..."
helm upgrade \
  --install dinghy-ping dinghy-ping/dinghy-ping \
  --namespace default \
  --set ingress.subdomain="localhost" \
  --set image.repository="${DOCKER_REPO}/${DOCKER_IMAGE_NAME}" \
  --set image.tag=dinghy_ping_test_${VER} 
