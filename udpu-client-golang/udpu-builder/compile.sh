#!/bin/bash

echo "Current directory: $(pwd)"

if [ ! -f ./udpu-builder/udpu.config ]; then
  echo "udpu.config: No such file or directory"
  exit 1
fi
source ./udpu-builder/udpu.config

ARCH=${GOARCH:-arm64}
CC_COMPILER=${CC_COMPILER:-/opt/cross/aarch64-linux-musl-cross/bin/aarch64-linux-musl-gcc}
VERSION=${CONFIG_VERSION_NUMBER}

echo "Building for architecture: $ARCH"
echo "Version: $VERSION"

mkdir -p ./dist

GOOS=linux GOARCH=$ARCH CGO_ENABLED=1 CC=$CC_COMPILER go build -o ./dist/dpu_client-${VERSION} -ldflags="-extldflags=-static" .

echo "Contents of ./dist after build:"
ls -la ./dist

tar -czvf ./dist/dpu_client-${VERSION}.tgz -C ./dist dpu_client-${VERSION}

echo "Contents of ./dist after creating archive:"
ls -la ./dist
