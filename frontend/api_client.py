import json
import requests

class APIClient:
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(self, method, path, payload=None, params=None):
        url = self.base_url + path
        try:
            response = requests.request(method, url, json=payload, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            return False, str(exc)
        try:
            data = response.json()
        except ValueError:
            data = response.text
        if response.ok:
            return True, data
        return False, data

    def get(self, path, params=None):
        return self._request('GET', path, params=params)

    def post(self, path, payload=None, params=None):
        return self._request('POST', path, payload=payload, params=params)

    def put(self, path, payload=None, params=None):
        return self._request('PUT', path, payload=payload, params=params)

    def patch(self, path, payload=None, params=None):
        return self._request('PATCH', path, payload=payload, params=params)

    def delete(self, path, params=None):
        return self._request('DELETE', path, params=params)


def parse_json(text):
    try:
        return True, json.loads(text) if text.strip() else {}
    except ValueError as exc:
        return False, str(exc)
