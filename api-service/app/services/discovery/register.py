import requests
from services.logging.logger import log as logger


def register_service(settings):
    """
    Register the service to the discovery server.
    """
    try:
        response = requests.post(
            url=settings.discovery_url,
            json={
                "host": settings.server_host,
                "port": settings.server_port,
                "service_type": "server"
            }
        )
        # If status code is not in 200–299 range, log a warning
        if 200 <= response.status_code < 300:
            # logger.info(
            #     f"Server registration successful: {response.status_code}; message: {response.text}"
            # )
            logger.info(
                f"Server registration successful: {response.status_code}"
            )
        else:
            logger.warning(
                f"Unexpected registration status: {response.status_code}; message: {response.text}"
            )
    except Exception as e:
        logger.exception(e)
