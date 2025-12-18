
class BaseEcp(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class RedisResponseError(BaseEcp):
    ...


class UdpuValidationError(BaseEcp):
    ...


class PoolExhaustedError(Exception):
    """Raised when no free /31 subnet is available in the pool."""


class RedisConnectionError(Exception):
    """Raised when unable to connect to Redis."""
