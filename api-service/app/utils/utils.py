import re
import secrets
import string
import uuid
from datetime import datetime
from typing import Iterable, Optional
from domain.api.northbound.constants import DATE_TIME_FORMAT


def validate_hostname(hostname: str) -> bool:
    """
    Validate a hostname according to RFC rules.

    :param hostname: Hostname to validate.
    :return: True if valid, False otherwise.
    """
    if hostname.endswith("."):
        hostname = hostname[:-1]
    if len(hostname) > 253:
        return False

    labels = hostname.split(".")
    # TLD must not be all-numeric
    if re.fullmatch(r"\d+", labels[-1]):
        return False

    pattern = re.compile(r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
    return all(pattern.fullmatch(label) for label in labels)


def generate_random_value(
    prefix: Optional[str], chars: str, size: int = 8
) -> str:
    """
    Generate a random string with optional prefix.

    :param prefix: Optional prefix to prepend.
    :param chars: Characters to choose from.
    :param size: Length of the random part.
    :return: Generated string.
    """
    random_part = "".join(secrets.choice(chars) for _ in range(size))
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part


def generate_udpu_hostname() -> str:
    """
    Generate a random uDPU hostname.

    :return: Hostname string.
    """
    chars = string.ascii_lowercase + string.digits
    return generate_random_value("udpu", chars, 8)


def generate_pppoe_username() -> str:
    """
    Generate a random PPPoE username.

    :return: Username string.
    """
    chars = string.ascii_lowercase + string.digits
    return generate_random_value("user", chars, 8)


def generate_pppoe_password() -> str:
    """
    Generate a random PPPoE password.

    :return: Password string.
    """
    chars = string.ascii_letters + string.digits
    return generate_random_value(None, chars, 12)


def get_vb_uid(udpu: str, ghn_interface: str) -> str:
    """
    Generate a deterministic UUID based on uDPU and interface names.

    :param udpu: uDPU identifier.
    :param ghn_interface: Interface name.
    :return: Hexadecimal UUID string.
    """
    name = udpu + ghn_interface
    return uuid.uuid5(uuid.NAMESPACE_DNS, name).hex


def get_random_seed_index(
    low: int, high: int, exclude: Iterable[int]
) -> int:
    """
    Get a random index in the range [low, high), excluding specified values.

    :param low: Inclusive lower bound.
    :param high: Exclusive upper bound.
    :param exclude: Iterable of indices to exclude.
    :return: Random index.
    :raises IndexError: If no valid index is available.
    """
    choices = [i for i in range(low, high) if i not in exclude]
    return secrets.choice(choices)


def get_provisioned_date() -> str:
    """
    Get the current date and time formatted according to DATE_TIME_FORMAT.

    :return: Formatted datetime string.
    """
    now = datetime.now().astimezone()
    return now.strftime(DATE_TIME_FORMAT)
