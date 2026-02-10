import inspect
import logging
import sys

from loguru import logger


class LoggerInterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a record.

        Attempt to extract the Loguru level from the LogRecord.
        If it fails, use the standard logging level number.
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class MainLogger:
    __instance = None

    def __new__(cls) -> "MainLogger":
        """
        Implement singleton pattern to ensure only one instance of MainLogger is created.
        """
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.logger = logger
        return cls.__instance

    def configure(
        self,
        log_level: str = "INFO",
        log_path: str = "./logs/app.log",
        log_format: str = None,
        colorize: bool = True,
        rotation: str = "00:00",
        retention: str = "10 days",
    ) -> None:
        """
        Configure the logger with specified settings.

        :param log_level: Logging level (e.g., "INFO", "DEBUG")
        :param log_path: Path to the log file
        :param log_format: Format of the log messages
        :param colorize: Whether to colorize the log output
        :param rotation: Log rotation setting
        :param retention: Log retention setting
        """
        # Remove the standard handler
        self.logger.remove()
        # Set default format if not provided
        if log_format is None:
            log_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level}</level> | "
                "<level>{message}</level>"
            )
        # Add console handler
        self.logger.add(
            sys.stdout,
            level=log_level,
            format=log_format,
            colorize=colorize,
        )
        # Add file handler
        self.logger.add(
            log_path,
            level=log_level,
            format=log_format,
            rotation=rotation,
            retention=retention,
        )

    @property
    def get_logger(self):
        """Get logger"""
        return self.__instance.logger


# Configure the basic logging to intercept with LoggerInterceptHandler
logging.basicConfig(handlers=[LoggerInterceptHandler()], level=0, force=True)

log = MainLogger()
log.configure()

log = log.get_logger
