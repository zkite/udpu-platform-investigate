#!/bin/bash

set -e

ARCH=${1:-arm64}

command -v git >/dev/null 2>&1 || { echo >&2 "git is required but it's not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo >&2 "docker is required but it's not installed. Aborting."; exit 1; }

LATEST_TAG=$(git describe --tags $(git rev-list --tags --max-count=1))

git checkout $LATEST_TAG

mkdir -p $(pwd)/dist

IMAGE_NAME=dpu-client-builder

docker build --build-arg GOARCH=$ARCH -t $IMAGE_NAME .

docker run -v $(pwd)/dist:/app/dist -w /app -e GOARCH=$ARCH -e LATEST_TAG=$LATEST_TAG $IMAGE_NAME
