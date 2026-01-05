import os
import asyncio
from urllib.parse import urlparse, urlunparse
import websockets


class WsError(Exception):
    pass


class WsClient:
    def __init__(self, base_url=None, timeout=None):
        http_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8888/api/v1.0")
        parsed = urlparse(http_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        path = parsed.path.rstrip("/")
        self.http_base = http_url
        self.ws_base = urlunparse((scheme, parsed.netloc, path, "", "", ""))
        self.timeout = float(timeout or os.getenv("WS_TIMEOUT", 10))
        self.connection = None

    def _full_url(self, path):
        return f"{self.ws_base}/{path.lstrip('/')}"

    async def _connect(self, path):
        url = self._full_url(path)
        self.connection = await websockets.connect(url, open_timeout=self.timeout, close_timeout=self.timeout)

    def connect(self, path):
        asyncio.run(self._connect(path))

    async def _disconnect(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

    def disconnect(self):
        asyncio.run(self._disconnect())

    async def _send(self, text):
        if not self.connection:
            raise WsError("Нет активного соединения")
        await self.connection.send(text)

    def send(self, text):
        asyncio.run(self._send(text))

    async def _ping(self):
        if not self.connection:
            raise WsError("Нет активного соединения")
        pong_waiter = await self.connection.ping()
        await asyncio.wait_for(pong_waiter, timeout=self.timeout)

    def ping(self):
        asyncio.run(self._ping())

    async def _receive(self, limit, timeout):
        results = []
        if not self.connection:
            raise WsError("Нет активного соединения")
        for _ in range(limit):
            try:
                msg = await asyncio.wait_for(self.connection.recv(), timeout)
                results.append(msg)
            except asyncio.TimeoutError:
                break
        return results

    def receive(self, limit=5, timeout=1.0):
        return asyncio.run(self._receive(limit, timeout))
