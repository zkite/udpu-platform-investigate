from typing import Dict, Optional

from services.logging.logger import log as logger
from redis import Redis
from redis.exceptions import RedisError
from domain.api.authentication.constants import CLIENT_STAMP
from domain.api.authentication.schemas import Stamp
from services.redis.exceptions import RedisResponseError


class StampService:
    """
    Service for managing stamps in Redis.
    """

    def __init__(self, redis: Redis):
        self._redis = redis

    @staticmethod
    def _format_key(mac_address: str) -> str:
        """
        Generate the Redis key for the given MAC address.

        :param mac_address: MAC address of the client.
        :return: Formatted Redis key.
        """
        return f"{CLIENT_STAMP}:{mac_address}"

    async def create(self, stamp: Stamp) -> None:
        """
        Create a new stamp in Redis.

        :param stamp: Stamp model containing mac_address and body.
        :raises ValueError: if stamp already exists.
        :raises RedisResponseError: if Redis operation fails.
        """
        key = self._format_key(stamp.mac_address)
        try:
            if await self._redis.exists(key):
                raise ValueError(f"Stamp for MAC {stamp.mac_address} already exists")
            await self._redis.set(key, stamp.body)
        except RedisError as e:
            logger.error(f"Redis error in create for key {key}: {e}", exc_info=True)
            raise RedisResponseError(str(e))

    async def get(self, mac_address: str) -> Optional[str]:
        """
        Retrieve a stamp body by MAC address.

        :param mac_address: MAC address of the client.
        :return: Body of the stamp, or None if not found.
        :raises RedisResponseError: if Redis operation fails.
        """
        key = self._format_key(mac_address)
        try:
            # decode_responses=True ensures this returns str or None
            return await self._redis.get(key)
        except RedisError as e:
            logger.error(f"Redis error in get for key {key}: {e}", exc_info=True)
            raise RedisResponseError(str(e))

    async def list_all(self) -> Dict[str, str]:
        """
        List all stamps stored in Redis.

        :return: Dict mapping mac_address to body.
        :raises RedisResponseError: if Redis operation fails.
        """
        pattern = f"{CLIENT_STAMP}:*"
        try:
            keys = await self._redis.keys(pattern)
            result: Dict[str, str] = {}
            for full_key in keys:
                _, mac = full_key.split(":", 1)
                body = await self._redis.get(full_key) or ""
                result[mac] = body
            return result
        except RedisError as e:
            logger.error(f"Redis error in list_all: {e}", exc_info=True)
            raise RedisResponseError(str(e))

    async def delete(self, mac_address: str) -> None:
        """
        Delete a stamp by MAC address.

        :param mac_address: MAC address of the client.
        :raises RedisResponseError: if Redis operation fails.
        """
        key = self._format_key(mac_address)
        try:
            await self._redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis error in delete for key {key}: {e}", exc_info=True)
            raise RedisResponseError(str(e))
