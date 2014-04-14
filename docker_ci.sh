#!/usr/bin/env bash
set -e

PROJECT=unicef/equitrack

echo '>>> Get current container id if exists'
CID=$(docker ps | grep $PROJECT | awk '{print $1}')
echo $CID

if [ "$CID" != "" ];
then
    echo '>>> Tagging current container'
    docker commit $CID $PROJECT:latest
fi

echo '>>> Building new image'
packer build packer.json
rc=$?
if [[ $rc != 0 ]] ; then
    exit $rc
fi

if [ "$CID" != "" ];
then
  echo '>>> Stopping old container'
  docker stop $CID
  docker commit $CID $PROJECT:old
  docker rm -f $CID
fi

echo '>>> Starting new container'
docker run -p 80:80 -d -e "DJANGO_ALLOWED_HOST=equitrack.uniceflebanon.org" $PROJECT:latest supervisord

echo '>>> Cleaning up containers'
docker ps -a | grep "Exit" | awk '{print $1}' | while read -r id ; do
  docker rm $id
done

echo '>>> Cleaning up images'
docker images | grep "^<none>" | awk 'BEGIN { FS = "[ \t]+" } { print $3 }'  | while read -r id ; do
  docker rmi $id
done

echo '>>> Finished, docker state:'
docker images
docker ps -a