# Use a slim Python 3.11.12 base image
FROM python:3.14.2-slim

# Ensure stdout and stderr are unbuffered
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /etc/wireguard

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends iputils-ping iproute2 \
 && rm -rf /var/lib/apt/lists/*

# Install WireGuard, necessary tools, and cleanup
# Note: wireguard-tools includes wg, wg-quick commands
# Added build-essential and python3-dev to fix the psutil build error
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        net-tools \
        build-essential \
        python3-dev \
        libffi-dev \
        gcc \
        linux-libc-dev \
        wireguard-tools \
        wireguard \
        iproute2 \
        iptables \
        redis-tools \
        netcat-openbsd \
        procps && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
COPY ../requirements/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy the application files
COPY ../app ./

# Run the application with Gunicorn and Uvicorn workers
CMD gunicorn -w 4 -k worker.UvicornWSWorker -b 0.0.0.0:8888 main:app \
    --worker-connections 30 \
    --keep-alive 10 \
    --timeout 20

