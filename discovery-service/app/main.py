import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from config import get_app_settings
from domain.api import routers
from events import create_start_app_handler, create_stop_app_handler
from exceptions.handlers.http_error import http_error_handler
from exceptions.handlers.validation_error import http422_error_handler
from settings.base import BaseAppSettings

settings = get_app_settings()


def get_application(settings: BaseAppSettings) -> FastAPI:

    application = FastAPI(**settings.fastapi_kwargs)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.add_event_handler(
        "startup",
        create_start_app_handler(application, settings),
    )
    application.add_event_handler(
        "shutdown",
        create_stop_app_handler(application),
    )

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, http422_error_handler)

    for router in routers:
        application.include_router(router, prefix="/api/v1.0")

    return application


app = get_application(settings)


if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8888, reload=True)
