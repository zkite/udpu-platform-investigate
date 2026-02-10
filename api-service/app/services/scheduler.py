from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from services.logging.logger import log as logger


def start_scheduler(app: FastAPI, func=None, args=None) -> None:
    logger.info("Starting the scheduler")
    app.scheduler = AsyncIOScheduler()

    app.scheduler.add_job(func, args=args, trigger="cron", second="*/30")
    app.scheduler.start()
    logger.info("Scheduler started")


def vbce_scheduler(app: FastAPI, func=None, args=None) -> None:
    logger.info("Starting the vbce scheduler")
    app.scheduler = AsyncIOScheduler()

    app.scheduler.add_job(func, args=args, trigger="cron", minute="*/2")
    app.scheduler.start()
    logger.info("VBCE scheduler started")


def shutdown_scheduler(app: FastAPI) -> None:
    logger.info("Stoping the scheduler")
    app.scheduler.shutdown()
    logger.info("Scheduler stopped")
