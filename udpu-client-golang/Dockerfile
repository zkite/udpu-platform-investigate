FROM golang:1.23 as builder

RUN apt-get update && apt-get install -y \
    gcc \
    musl-tools \
    git \
    wget \
    curl \
    build-essential

RUN mkdir -p /opt/cross && \
    wget https://musl.cc/aarch64-linux-musl-cross.tgz && \
    tar -C /opt/cross -xzf aarch64-linux-musl-cross.tgz && \
    rm aarch64-linux-musl-cross.tgz

ENV PATH=$PATH:/opt/cross/aarch64-linux-musl-cross/bin

WORKDIR /app

COPY . .

CMD ["/bin/bash", "./udpu-builder/compile.sh"]