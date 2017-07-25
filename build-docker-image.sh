#!/bin/bash

# Adapted from: https://gist.github.com/rshk/beecd2c49f81a380d805c8b461b4c704


# Version tag needs to be dependent on all the files that will affect
# the generated image. Currently, only the dockerfile and Python
# requirements.
VERSION_TAG="$( sha1sum Dockerfile EquiTrack/requirements/*.txt | sha1sum | cut -d' ' -f1 )"

echo "Image version: ${VERSION_TAG}"
echo "Commit branch: ${CIRCLE_BRANCH}"

IMAGE_FULL_NAME="unicef/etools:${VERSION_TAG}"
echo "Image name:    ${IMAGE_FULL_NAME}"

echo

# Cache dir must match the one configured in circle.yml
CACHE_DIR="$( readlink -f ~/docker )"

IMAGE_ARCHIVE="${CACHE_DIR}/etools-${VERSION_TAG}.tar"

echo "=====> Locating image archive: ${IMAGE_ARCHIVE}"

mkdir -p "$CACHE_DIR"

# If we already have an image built on the same dependencies, just
# re-use it.
if [[ -e "$IMAGE_ARCHIVE" ]]; then
    echo "-----> Loading existing image archive"
    docker load -i "$IMAGE_ARCHIVE"
else
    echo "=====> Building image: ${IMAGE_FULL_NAME}"
    docker build --rm=false -t "$IMAGE_FULL_NAME" .
fi

# Tag the image as being the correct one for this commit.
# This is used in circle.yml to pick the correct image.
echo "=====> Tagging image with branch-name: ${CIRCLE_BRANCH}"
docker tag "$IMAGE_FULL_NAME" unicef/etools:"$CIRCLE_BRANCH"

# Save to cache for later reuse
echo "=====> Saving image to cache: ${IMAGE_ARCHIVE}"
docker save "$IMAGE_FULL_NAME" > "$IMAGE_ARCHIVE"

echo "=====> All done."
