from __future__ import annotations

import socket
import subprocess

import logging
import re
import asyncio
from typing import Optional, List
import ipaddress
from datetime import datetime, timezone

from fastapi.security import HTTPBasic
from redis.asyncio.client import Redis
from redis.exceptions import ReadOnlyError, ResponseError

from domain.api.northbound.exceptions import PoolExhaustedError, RedisConnectionError
from utils import validate_hostname
from utils.utils import get_provisioned_date
from config import get_app_settings
from .constants import MAC_ADDRESS_KEY, PPPOE_ENTITY, UDPU_ENTITY, LOCATION_PREFIX, STATUS_PREFIX, OFFLINE_THRESHOLD
from .exceptions import RedisResponseError
from .schemas import Udpu, UdpuUpdate, UdpuStatus, UdpuStatusEnum


settings = get_app_settings()
security = HTTPBasic()


async def is_unique_mac_address(redis: Redis, mac_address: str) -> bool:
    return not await redis.sismember(f"{UDPU_ENTITY}:mac_address_list", mac_address)


async def is_unique_hostname(redis: Redis, hostname: str) -> bool:
    return not await redis.sismember(f"{UDPU_ENTITY}:hostname_list", hostname)


async def map_mac_address_to_subscriber(redis: Redis, mac_address_key: str, subscriber_key: str) -> bool:
    try:
        return await redis.set(mac_address_key, subscriber_key)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def update_udpu_list(redis: Redis, key: str, value: str) -> None:
    try:
        await redis.sadd(key, value)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_udpu_location_list(redis: Redis) -> set:
    try:
        return await redis.smembers(f"{UDPU_ENTITY}:location_list")
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_subscribers_by_location(redis: Redis, location_id: str) -> List[str]:
    try:
        return list(await redis.smembers(f"{LOCATION_PREFIX}:{location_id}"))
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


def is_valid_mac_address(mac_address: str) -> bool:
    return bool(re.match(r"[0-9a-fA-F]{2}([-:]?)[0-9a-fA-F]{2}(\1[0-9a-fA-F]{2}){4}$", mac_address))


def is_valid_hostname(hostname: str) -> bool:
    return bool(hostname and validate_hostname(hostname))


async def get_udpu(redis: Redis, key: str) -> dict:
    if not key.startswith(f"{UDPU_ENTITY}:"):
        key = f"{UDPU_ENTITY}:{key}"
    try:
        return await redis.hgetall(key)
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def update_udpu(redis: Redis, update_request: UdpuUpdate, udpu: dict) -> dict:
    try:
        update_data = update_request.dict()
        update_data.update({
            "mac_address_key": f"{MAC_ADDRESS_KEY}:{update_request.mac_address}",
            "subscriber_key": f"{UDPU_ENTITY}:{udpu['subscriber_uid']}",
            "subscriber_uid": udpu["subscriber_uid"],
        })

        pipe = redis.pipeline(transaction=True)

        pipe.srem(f"{UDPU_ENTITY}:mac_address_list", udpu["mac_address"])
        pipe.srem(f"{LOCATION_PREFIX}:{udpu['location']}", udpu["subscriber_uid"])

        pipe.sadd(f"{UDPU_ENTITY}:mac_address_list", update_data["mac_address"])
        pipe.sadd(f"{UDPU_ENTITY}:location_list", update_data["location"])
        pipe.sadd(f"{LOCATION_PREFIX}:{update_data['location']}", update_data["subscriber_uid"])

        pipe.set(update_data["mac_address_key"], update_data["subscriber_key"])
        pipe.hset(update_data["subscriber_key"], mapping=update_data)

        if udpu["mac_address"] != update_data["mac_address"]:
            pipe.delete(f"{MAC_ADDRESS_KEY}:{udpu['mac_address']}")

        await pipe.execute()
        return await get_udpu(redis, update_data["subscriber_uid"])
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def delete_udpu(redis: Redis, udpu: dict) -> None:
    try:
        pipe = redis.pipeline(transaction=True)
        pipe.delete(f"{UDPU_ENTITY}:{udpu['subscriber_uid']}")
        pipe.delete(f"{MAC_ADDRESS_KEY}:{udpu['mac_address']}")
        pipe.delete(f"{PPPOE_ENTITY}:{udpu['subscriber_uid']}")
        pipe.srem(f"{UDPU_ENTITY}:mac_address_list", udpu["mac_address"])
        pipe.srem(f"{UDPU_ENTITY}:hostname_list", udpu["hostname"])
        await pipe.execute()
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def create_udpu(redis: Redis, udpu: Udpu) -> None:
    try:
        data = udpu.dict(exclude_none=True)
        await redis.hset(udpu.subscriber_key, mapping=data)
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def save_pppoe_credentials(redis: Redis, pppoe_creds) -> None:
    try:
        await redis.hset(pppoe_creds.subscriber_key, mapping=pppoe_creds.dict())
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def bulk_update_udpu(redis: Redis, udpu_lst: List[dict], update_request) -> List[dict]:
    pipe = redis.pipeline()
    updated_list = []

    for udpu in udpu_lst:
        udpu.update({
            "role": update_request.role,
            "upstream_qos": update_request.upstream_qos,
            "downstream_qos": update_request.downstream_qos,
            "provisioned_last_date": get_provisioned_date()
        })
        await pipe.hset(f"{UDPU_ENTITY}:{udpu['subscriber_uid']}", mapping=udpu)
        updated_list.append(udpu)

    await pipe.execute()
    return updated_list


async def get_udpu_by_mac_address(redis: Redis, key: str) -> Optional[dict]:
    try:
        subscriber_key = await redis.get(key)
        if subscriber_key:
            return await get_udpu(redis, subscriber_key)
        return None
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def get_subscriber_key_by_mac_addr(redis: Redis, mac_address: str):
    try:
        async for key in redis.scan_iter(match=f"{UDPU_ENTITY}:*"):
            try:
                if await redis.type(key) != "hash":
                    continue

                value = await redis.hget(key, "mac_address")
                if value is None:
                    continue

                if value.lower() == mac_address.lower():
                    return key
            except ResponseError:
                continue

        return None
    except ResponseError as e:
        logging.error(f"Redis error: {e}")
        raise RedisResponseError(message=str(e))


async def delete_udpu_by_mac_address(redis: Redis, mac_address: str) -> Optional[dict]:
    try:
        udpu = await get_udpu_by_mac_address(redis, mac_address)
        if udpu:
            await delete_udpu(redis, udpu)
        return udpu
    except ResponseError as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


async def initialize_client_ip_pool(redis: Redis) -> None:
    if await redis.exists(settings.FREE_CLIENT_IPS_KEY):
        return

    server_ip = ipaddress.IPv4Address(settings.WG_SERVER_IP.split("/")[0])
    ips: List[str] = []

    for pool in settings.DEFAULT_POOL.split(","):
        net = ipaddress.IPv4Network(pool.strip(), strict=False)
        ips.extend(
            f"{host}/32"
            for host in net.hosts()
            if host != server_ip
        )

    pipe = redis.pipeline()
    for ip in ips:
        pipe.sadd(settings.FREE_CLIENT_IPS_KEY, ip)
    await pipe.execute()


async def generate_client_ip(redis: Redis) -> str:
    await initialize_client_ip_pool(redis)

    for attempt in range(1, settings.WG_MAX_RETRIES + 1):
        try:
            ip = await redis.spop(settings.FREE_CLIENT_IPS_KEY)
            if not ip:
                raise PoolExhaustedError()

            if not await redis.sadd(settings.ALLOCATED_CLIENT_IPS_KEY, ip):
                await redis.sadd(settings.FREE_CLIENT_IPS_KEY, ip)
                raise Exception("Allocation failed")

            return ip

        except (PoolExhaustedError, Exception) as e:
            logging.warning(
                "Redis error on generate_client_ip attempt %d/%d: %s",
                attempt, settings.WG_MAX_RETRIES, e
            )
            if attempt >= settings.WG_MAX_RETRIES:
                raise RedisConnectionError(
                    "Failed to allocate client IP: Redis unavailable."
                ) from e
            backoff = settings.WG_BACKOFF_FACTOR * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)

    raise RedisConnectionError("Failed to allocate client IP after retries.")


class WireGuardError(RuntimeError):
    ...


def get_public_key(interface: str = "wg0", sudo: bool = True) -> str:
    try:
        cmd: List[str] = (["sudo"] if sudo else []) + [
            "wg",
            "show",
            interface,
            "public-key",
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            return ""

        return proc.stdout.strip()
    except Exception:
        return ""


def get_local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]

def status_key(subscriber_uid: str) -> str:
    return f"{STATUS_PREFIX}:{subscriber_uid}"

def _ensure_str_dict(d):
    out = {}
    for k, v in d.items():
        ks = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
        if isinstance(v, (bytes, bytearray)):
            vs = v.decode()
        elif isinstance(v, (int, float)):
            vs = str(v)
        elif isinstance(v, str):
            vs = v
        elif v is None:
            vs = ""
        else:
            vs = str(v)
        out[ks] = vs
    return out

def _to_mapping(u: UdpuStatus):
    d = u.model_dump(exclude_none=True)
    if u.state is not None:
        d["state"] = u.state
    if u.status is not None:
        d["status"] = u.status
    d["created_at"] = str(d["created_at"])
    return d

def _from_hash(subscriber_uid, h) -> UdpuStatus:
    if not h:
        return None
    d = _ensure_str_dict(h)
    if "registered" in d:
        d["registered"] = d["registered"] in ("1", "true", "True", "yes", "Y")
    d.setdefault("subscriber_uid", subscriber_uid)
    try:
        return UdpuStatus(**d)
    except Exception as e:
        logging.error(f"UdpuStatus validation error for {subscriber_uid}: {e}")
        return None

# ----- CRUD -----

async def create_udpu_status(redis: Redis, data: UdpuStatus) -> None:
    try:
        key = status_key(data.subscriber_uid)
        await redis.hset(key, mapping=_to_mapping(data))
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))

async def get_udpu_status(redis: Redis, subscriber_uid: str) -> Optional[UdpuStatus]:
    key = status_key(subscriber_uid)
    try:
        h = await redis.hgetall(key)
        if not h:
            return
        data = _from_hash(subscriber_uid, h)
        return _apply_offline_if_stale(data)
    except Exception as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))

async def update_udpu_status(redis: Redis, data: UdpuStatus) -> None:
    try:
        key = status_key(data.subscriber_uid)
        await redis.hset(key, mapping=_to_mapping(data))
    except (ResponseError, ReadOnlyError) as e:
        logging.error(str(e))
        raise RedisResponseError(message=str(e))


def _apply_offline_if_stale(model: UdpuStatus) -> UdpuStatus:

    ts = model.created_at
    if ts is None:
        model.status = UdpuStatusEnum.OFFLINE

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) - ts > OFFLINE_THRESHOLD:
        if model.status != UdpuStatusEnum.OFFLINE:
            model.status = UdpuStatusEnum.OFFLINE
    return model