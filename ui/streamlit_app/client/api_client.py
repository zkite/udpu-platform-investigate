import os
import json
import requests


class ApiError(Exception):
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(self.message)

    @property
    def message(self):
        if isinstance(self.payload, dict):
            return self.payload.get("message") or self.payload.get("detail") or json.dumps(self.payload, ensure_ascii=False)
        return str(self.payload)


class ApiClient:
    def __init__(self, base_url=None, timeout=None):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8888/api/v1.0")
        self.timeout = float(timeout or os.getenv("API_TIMEOUT", 10))

    def _url(self, path):
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _handle(self, resp):
        try:
            data = resp.json()
        except ValueError:
            data = resp.text
        if resp.status_code >= 400:
            raise ApiError(resp.status_code, data)
        return data

    def request(self, method, path, json=None, params=None):
        url = self._url(path)
        try:
            resp = requests.request(method, url, timeout=self.timeout, json=json, params=params)
            return self._handle(resp)
        except requests.RequestException as e:
            raise ApiError(0, str(e))

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def post(self, path, payload=None):
        return self.request("POST", path, json=payload)

    def patch(self, path, payload=None):
        return self.request("PATCH", path, json=payload)

    def delete(self, path):
        return self.request("DELETE", path)
