from typing import List
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_utils.cbv import cbv

from config import get_app_settings
from domain.api.jobs.queues.core import QueueRepository
from domain.api.jobs.queues.schemas import JobQueueSchema

router = APIRouter()


def get_queue_repository(request: Request) -> QueueRepository:
    """
    Dependency to retrieve the QueueRepository initialized with Redis client.
    """
    return QueueRepository(request.app.state.redis)


@cbv(router)
class JobQueueAPI:
    """
    API endpoints for managing job queues.
    """
    settings = get_app_settings()
    repo: QueueRepository = Depends(get_queue_repository)

    @router.get("/queues", response_model=List[JobQueueSchema])
    async def list_queues(self) -> List[JobQueueSchema]:
        """
        Retrieve all job queues.
        """
        queues = await self.repo.get_all()
        if not queues:
            raise HTTPException(status_code=404, detail="No queues found")
        return queues

    @router.post("/queues", response_model=JobQueueSchema, status_code=201)
    async def create_queue(self, payload: JobQueueSchema) -> JobQueueSchema:
        """
        Create a new job queue with unique role and name, validating referenced jobs.
        """
        if await self.repo.get(payload.name):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Queue name '{payload.name}' already exists",
            )
        if not await self.repo.is_role_unique(payload.role):
            raise HTTPException(status_code=400, detail=f"Queue role '{payload.role}' already exists")
        invalid_jobs = await self.repo.validate_jobs(payload.queue)
        if invalid_jobs:
            raise HTTPException(status_code=400, detail=f"Job(s) '{', '.join(invalid_jobs)}' do not exist")
        return await self.repo.create(payload)

    @router.get("/queues/{identifier}", response_model=JobQueueSchema)
    async def get_queue(self, identifier: str) -> JobQueueSchema:
        """
        Retrieve a job queue by UID or name.
        """
        queue = await self.repo.get(identifier)
        if not queue:
            raise HTTPException(status_code=404, detail=f"Queue '{identifier}' not found")
        return queue

    @router.patch("/queues/{identifier}", response_model=JobQueueSchema)
    async def update_queue(self, identifier: str, payload: JobQueueSchema) -> JobQueueSchema:
        """
        Update an existing job queue identified by UID or name.
        """
        existing = await self.repo.get(identifier)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Queue '{identifier}' not found")
        if payload.name != existing.name and await self.repo.get(payload.name):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Queue name '{payload.name}' already exists",
            )
        if not await self.repo.is_role_unique(payload.role, exclude_identifier=identifier):
            raise HTTPException(status_code=400, detail=f"Queue role '{payload.role}' already exists")
        invalid_jobs = await self.repo.validate_jobs(payload.queue)
        if invalid_jobs:
            raise HTTPException(status_code=400, detail=f"Job(s) '{', '.join(invalid_jobs)}' do not exist")
        updated = await self.repo.update(
            identifier,
            payload.model_dump(exclude_unset=True, exclude={"uid"}),
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Queue '{identifier}' not found")
        return updated

    @router.delete("/queues/{identifier}")
    async def delete_queue(self, identifier: str) -> dict[str, str]:
        """
        Delete a job queue by UID or name.
        """
        existing = await self.repo.get(identifier)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Queue '{identifier}' not found")
        await self.repo.delete(identifier)
        return {"message": f"Queue '{identifier}' deleted successfully"}

    @router.get("/roles/{role_name}/queues", response_model=List[JobQueueSchema])
    async def get_queues_by_role(self, role_name: str) -> List[JobQueueSchema]:
        """
        Retrieve all queues assigned to a specific role.
        """
        queues = await self.repo.get_by_role(role_name)
        if not queues:
            raise HTTPException(status_code=404, detail=f"No queues found for role '{role_name}'")
        return queues
