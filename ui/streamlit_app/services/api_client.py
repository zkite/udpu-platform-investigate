import os
import requests

class APIClient:
    def __init__(self):
        self.base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8888/api/v1.0").rstrip("/")
        self.timeout = float(os.getenv("UI_REQUEST_TIMEOUT", "5"))
        self.session = requests.Session()

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except Exception as exc:
            return False, None, str(exc)
        try:
            data = response.json()
        except Exception:
            data = response.text
        if 200 <= response.status_code < 300:
            return True, data, None
        message = None
        if isinstance(data, dict):
            message = data.get("message") or data.get("detail")
        if not message:
            message = f"HTTP {response.status_code}"
        return False, data, message

    def get_roles(self):
        return self._request("get", "/roles")

    def create_role(self, payload):
        return self._request("post", "/roles", json=payload)

    def update_role(self, name, payload):
        return self._request("patch", f"/roles/{name}", json=payload)

    def delete_role(self, name):
        return self._request("delete", f"/roles/{name}")

    def get_udpu_locations(self):
        return self._request("get", "/udpu/locations")

    def get_udpu_list_by_location(self, location):
        return self._request("get", f"/{location}/udpu_list")

    def create_udpu(self, payload):
        return self._request("post", "/udpu", json=payload)

    def update_udpu(self, subscriber_uid, payload):
        return self._request("put", f"/subscriber/{subscriber_uid}/udpu", json=payload)

    def delete_udpu(self, subscriber_uid):
        return self._request("delete", f"/subscriber/{subscriber_uid}/udpu")

    def get_jobs(self, name=None):
        path = "/jobs"
        if name:
            path = f"/jobs?name={name}"
        return self._request("get", path)

    def create_job(self, payload):
        return self._request("post", "/jobs", json=payload)

    def update_job(self, identifier, payload):
        return self._request("patch", f"/jobs/{identifier}", json=payload)

    def delete_job(self, identifier):
        return self._request("delete", f"/jobs/{identifier}")
