import re
import json
import uvicorn

from fastapi import FastAPI, Request

from starlette.middleware.cors import CORSMiddleware

from normality import collapse_spaces

from config import get_app_settings
from domain.api import routers
from events import create_start_app_handler, create_stop_app_handler
from settings.base import BaseAppSettings
from services.logging.logger import log as logger


settings = get_app_settings()


def get_application(settings: BaseAppSettings) -> FastAPI:
    """
    Create and configure FastAPI application.

    :param settings: Application settings instance.
    :return: Configured FastAPI application.
    """

    app = FastAPI(**settings.fastapi_kwargs)

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],

    )

    # Add startup and shutdown event handlers
    app.add_event_handler(
        "startup",
        create_start_app_handler(app, settings),
    )
    app.add_event_handler(
        "shutdown",
        create_stop_app_handler(app),
    )

    # Include API routers
    for router in routers:
        app.include_router(router, prefix="/api/v1.0")

    return app


app = get_application(settings)


def process_json_body(data: str) -> str:
    """
    Process and normalize JSON body text.

    :param data: Raw JSON string.
    :return: Minified JSON string or string with collapsed spaces.
    """
    try:
        #logger.info("Original data: %s", data)
        normalized_data = collapse_spaces(data)
        #logger.info("Normalized data: %s", normalized_data)
        data_json = json.loads(normalized_data)
        return json.dumps(data_json, separators=(',', ':'))
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        return re.sub(r'\s+', '', data)


@app.middleware("http")
async def preprocess_request_body(request: Request, call_next):
    """
    Middleware to preprocess the request body by normalizing JSON.

    :param request: Incoming HTTP request.
    :param call_next: Callable to pass the request to the next middleware or route handler.
    :return: HTTP response.
    """
    body_bytes = await request.body()
    content_type = request.headers.get("Content-Type", "")

    # Process the body only for JSON content
    if "application/json" in content_type:
        body_str = body_bytes.decode("utf-8")
        if not body_str:
            response = await call_next(request)
            return response

        fixed_body = process_json_body(body_str)

        async def receive():
            return {"type": "http.request", "body": fixed_body.encode("utf-8")}

        # Replace the original receive method with the new one
        request._receive = receive

    response = await call_next(request)
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)
