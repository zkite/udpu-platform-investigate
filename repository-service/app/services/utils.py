import hashlib
import os
import uuid
from functools import wraps
from http import HTTPStatus
from io import BytesIO
from typing import Callable

import requests

from domain.api.repository.constants import (DOWNLOADS_FOLDER,
                                                 FILE_CHUNK_SIZE)


def redis_key_prefix(prefix: str):
    """Add prefix to the 'redis key' function argument"""

    def function(function: Callable):
        @wraps(function)
        def wrapper(*args: list, **kwargs: dict):
            if len(args) == 2:
                redis, key = args
                return function(redis, f"{prefix}_{key}")
            elif len(args) == 1 and len(kwargs.values()) == 1:
                (redis,) = args
                try:
                    key = kwargs["key"]
                except KeyError:
                    raise TypeError("Incorrect function arguments. The 'key' argument is missed.")
                return function(redis, f"{prefix}_{key}")
            elif len(args) == 0 and len(kwargs.values()) == 2:
                try:
                    redis, key = kwargs["redis"], kwargs["key"]
                except KeyError:
                    raise TypeError("Incorrect function arguments. The 'key' argument is missed.")
                return function(redis, f"{prefix}_{key}")
            else:
                raise TypeError("Incorrect function arguments. The 'key' argument is missed.")

        return wrapper

    return function


def decode_dict(dct: dict) -> dict:
    data = {}
    for k, v in dct.items():
        key = k
        data[key] = v

    return data


def get_hashed_software_uid(url, password):
    return uuid.uuid5(uuid.NAMESPACE_DNS, url + password).hex


def get_sha256_checksum(file_url):
    response = requests.get(file_url, stream=True)
    if response.status_code == HTTPStatus.OK:
        if not os.path.exists(DOWNLOADS_FOLDER):
            # Create a new directory because it does not exist
            os.makedirs(DOWNLOADS_FOLDER)

        file = BytesIO()
        for chunk in response.iter_content(chunk_size=FILE_CHUNK_SIZE):
            if chunk:
                file.write(chunk)
        sha256_checksum = hashlib.sha256(file.read()).hexdigest()
        file.close()

        return sha256_checksum
    return None
