from uvicorn.workers import UvicornWorker


class UvicornWSWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "ws": "websockets",
        "ws_ping_interval": 20,
        "ws_ping_timeout": 30,
    }
