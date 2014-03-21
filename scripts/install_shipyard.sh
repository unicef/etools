#!/bin/bash -x

echo Setting up docker for shipyard...
echo 'DOCKER_OPTS="-H tcp://0.0.0.0:4243 -H unix:///var/run/docker.sock"' >> /etc/default/docker

docker pull shipyard/deploy

docker run -i -t -v /var/run/docker.sock:/docker.sock shipyard/deploy setup