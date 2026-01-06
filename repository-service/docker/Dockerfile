# Use a slim Python 3.11.12 base image
FROM python:3.14.2-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y procps && \
    apt-get install -y redis-tools && \
    apt-get install -y --no-install-recommends \
        netcat-openbsd \
        build-essential \
        python3-dev \
        libffi-dev \
        linux-libc-dev && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --upgrade pip
COPY ../requirements/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY ../app ./

CMD uvicorn --host 0.0.0.0 --port 8887 main:app --reload
