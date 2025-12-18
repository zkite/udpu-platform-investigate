from http import HTTPStatus
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv

from domain.api.jobs.schemas import JobSchema, JobSchemaUpdate, JobFrequency
from domain.api.jobs.core import JobRepository
from domain.api.jobs.dependencies import get_repository

router = APIRouter()


@cbv(router)
class JobsAPI:
    repo: JobRepository = Depends(get_repository)

    @router.get("/jobs", response_model=List[JobSchema])
    async def list_jobs(self, name: Optional[str] = None):
        if name:
            job = await self.repo.get(name)
            if not job:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"No jobs found for filter '{name}'",
                )
            return [job]
        return await self.repo.get_all()

    @router.post("/jobs", response_model=JobSchema, status_code=HTTPStatus.CREATED)
    async def create_job(self, job: JobSchema):
        if await self.repo.get(job.name):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Job name '{job.name}' already exists",
            )
        return await self.repo.create(job)

    @router.get("/jobs/{identifier}", response_model=JobSchema)
    async def get_job(self, identifier: str):
        job = await self.repo.get(identifier)
        if not job:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Job '{identifier}' not found",
            )
        return job

    @router.patch("/jobs/{identifier}", response_model=JobSchema)
    async def update_job(self, identifier: str, payload: JobSchemaUpdate):
        update_data = payload.model_dump(exclude_unset=True)
        updated = await self.repo.update(identifier, update_data)
        if not updated:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Job '{identifier}' not found",
            )
        return updated

    @router.delete("/jobs/{identifier}")
    async def delete_job(self, identifier: str):
        if not await self.repo.delete(identifier):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Job '{identifier}' not found",
            )
        return {"message": f"Job '{identifier}' deleted successfully"}

    @router.get("/roles/{role_name}/jobs", response_model=List[JobSchema])
    async def get_jobs_by_role(
        self,
        role_name: str,
        frequency: Optional[JobFrequency] = None,  # ?frequency=first_boot|1|15|60|1440|every_boot|once
    ):
        freq = frequency or JobFrequency.FIRST_BOOT
        jobs = await self.repo.get_by_role(role_name, freq)
        if not jobs:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"No jobs found for role '{role_name}'",
            )
        return jobs

    @router.get("/jobs/frequency/{frequency}", response_model=List[JobSchema])
    async def get_jobs_by_frequency(self, frequency: JobFrequency):
        jobs = await self.repo.get_by_frequency(frequency)
        if not jobs:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"No jobs found for frequency '{frequency.value}'",
            )
        return jobs
