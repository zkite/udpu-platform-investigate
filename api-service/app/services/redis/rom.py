from redis.asyncio.client import Redis
import hashlib
import json


class ROM:
    """
    A class to manage Redis objects with a generated key based on provided hash keys.

    The Redis connection is maintained at the class level.

    :param prefix: The prefix for the Redis key.
    :param obj: The dictionary representing the object data.
    :param hash_keys: A tuple of keys from obj to generate a unique hash for the key.
    """
    # Class-level Redis connection
    _redis: Redis = None

    @classmethod
    def init_connection(cls, redis: Redis):
        """
        Initialize the class-level Redis connection.

        :param redis: The Redis connection instance.
        """
        cls._redis = redis

    def __init__(self, prefix: str, obj: dict, hash_keys: tuple):
        """
        Initialize a new ROM instance.

        :param prefix: The prefix for the Redis key.
        :param obj: The dictionary containing object data.
        :param hash_keys: Tuple of keys used to generate a unique hash for the object.
        """
        if self.__class__._redis is None:
            raise Exception("Redis connection is not configured. Please call ROM.init_connection(redis) first.")
        self._prefix = prefix
        self._obj = obj
        self._key = None
        self._hash_keys = hash_keys

    @property
    def key(self) -> str:
        """
        Compute or return the Redis key for the object.
        """
        if self._key is None:
            self._key = f"{self._prefix}_{self.__generate_hash()}"
        return self._key

    def __generate_hash(self) -> str:
        """
        Generate a hash based on selected object keys.

        :return: A 12-character long hash string.
        """
        combined = ""
        for k in self._hash_keys:
            combined += self._obj.get(k, "")
        full_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        return full_hash[:12]

    async def get(self):
        """
        Retrieve the JSON stored object from Redis and return it as a new ROM instance.
        If no object is found, return an empty dictionary.
        """
        obj = await self.__class__._redis.get(self.key)
        if obj:
            return ROM(prefix=self._prefix, obj=json.loads(obj), hash_keys=self._hash_keys)
        return {}

    async def delete(self):
        """
        Delete the stored object from Redis and reset the instance attributes.
        """
        await self.__class__._redis.delete(self.key)
        self._obj, self._key, self._hash_keys = {}, "", ()
        return self

    async def save(self):
        """
        Save the current object (as JSON) into Redis.
        """
        await self.__class__._redis.set(self.key, json.dumps(self._obj))
        return self

    def __getitem__(self, item):
        """
        Allow dictionary-like access to the object attributes.
        """
        if item == "key":
            return self.key
        try:
            return self._obj[item]
        except KeyError as e:
            raise KeyError(f"Key '{item}' not found") from e

    def __setitem__(self, item, value):
        """
        Allow setting new values to the object attributes in a dictionary-like manner.
        """
        if item == "key":
            raise KeyError("Cannot modify reserved attribute 'key'")
        self._obj[item] = value

    def __delitem__(self, item):
        """
        Allow deletion of object attributes in a dictionary-like manner.
        """
        if item == "key":
            raise KeyError("Cannot delete reserved attribute 'key'")
        try:
            del self._obj[item]
        except KeyError as e:
            raise KeyError(f"Key '{item}' not found") from e

    def __iter__(self):
        """
        Return iterator that includes the computed key and all keys of the object.
        """
        return iter(["key"] + list(self._obj.keys()))

    def __len__(self):
        """
        Return the total number of keys including the computed key.
        """
        return 1 + len(self._obj)

    def __getattr__(self, item):
        """
        Allow access to the object attributes as if they were fields.
        """
        try:
            return self._obj[item]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    @classmethod
    async def get_by(cls, prefix, k, hash_keys):
        """
        Retrieve the JSON stored object by key from Redis and return it as a new ROM instance.
        If no object is found, return an empty dictionary.
        """

        obj = await cls._redis.get(f"{prefix}_{k}")
        if obj:
            return ROM(prefix=prefix, obj=json.loads(obj), hash_keys=hash_keys)
        return {}

    @classmethod
    async def get_all(cls, prefix: str, hash_keys: tuple) -> list:
        """
        Retrieve all objects from Redis with the given prefix and create ROM instances for each.

        :param prefix: The prefix for filtering Redis keys.
        :param hash_keys: The tuple of keys used for object identification.
        :return: A list of ROM instances.
        """
        results = []
        async for key in cls._redis.scan_iter(match=f"{prefix}_*"):
            obj_data = await cls._redis.get(key)
            if obj_data:
                obj = json.loads(obj_data)
                results.append(cls(prefix=prefix, obj=obj, hash_keys=hash_keys))
        return results

    @classmethod
    async def filtered(cls, prefix: str, hash_keys: tuple, v: str) -> list:
        """
        Retrieve all objects using get_all and filter those that contain the substring 'v'
        in either the 'uid' or 'name' field.

        :param prefix: The prefix used in Redis keys.
        :param hash_keys: The tuple of keys used to generate the object hash.
        :param v: The substring to search within 'uid' or 'name' fields.
        :return: A list of ROM instances matching the filter criteria.
        """
        all_objects = await cls.get_all(prefix=prefix, hash_keys=hash_keys)
        filtered_objs = [
            obj for obj in all_objects
            if v in obj._obj.get("uid", "") or v in obj._obj.get("name", "")
        ]
        return filtered_objs
