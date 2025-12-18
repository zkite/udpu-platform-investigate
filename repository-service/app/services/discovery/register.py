import requests
from services.logging.logger import log as logger


def register_service(settings):
    try:
        response = requests.post(
            url=settings.discovery_url,
            json={"host": settings.server_host, "port": settings.server_port, "service_type": "repo"})
        logger.info(f"Server registration status: {response.status_code}; message: {response.text}")
    except Exception as e:
        logger.exception(e)
