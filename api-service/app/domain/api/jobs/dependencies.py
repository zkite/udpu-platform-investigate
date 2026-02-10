from fastapi import Request
from domain.api.jobs.core import JobRepository


def get_repository(request: Request) -> JobRepository:
    return JobRepository(request.app.state.redis)