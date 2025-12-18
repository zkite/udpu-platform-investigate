
from fastapi_utils.cbv import cbv
from config import get_app_settings
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from domain.api.logs.core import JobLogService
from domain.api.logs.schemas import JobLogSchema

from domain.api.logs.dependencies import get_job_log_service


router = APIRouter()


@cbv(router)
class JobLogSchema:
    settings = get_app_settings()

    @router.get("/logs/jobs", response_model=List[JobLogSchema], status_code=status.HTTP_200_OK)
    async def list_job_logs(
            self,
            service: JobLogService = Depends(get_job_log_service),
    ):
        """
        List all job logs.
        """
        return await service.get_all()

    @router.post("/logs/jobs", response_model=JobLogSchema, status_code=status.HTTP_201_CREATED)
    async def create_job_log(
            self,
            job_log: JobLogSchema,
            service: JobLogService = Depends(get_job_log_service),
    ):
        """
        Create a new job log entry.
        """
        return await service.create(job_log)

    @router.get("/logs/jobs/{job_name}", response_model=List[JobLogSchema], status_code=status.HTTP_200_OK)
    async def get_logs_by_name(
            self,
            job_name: str,
            service: JobLogService = Depends(get_job_log_service),
    ):
        """
        Retrieve logs by job name.
        """
        return await service.get_by_name(job_name)
