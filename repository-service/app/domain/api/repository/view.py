from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter

from config import get_app_settings

from .dependencies import (create_repository, get_repository,
                           increment_number_of_downloads, patch_repository)
from .schemas import Repository

router = InferringRouter()


@cbv(router)
class RepositoryView:
    settings = get_app_settings()

    @router.post("/repo", response_model=Repository)
    async def post(self, repository: Repository, request: Request):
        redis = request.app.state.redis
        repository.calculate_software_uid()
        repository.calculate_sha256_checksum()

        if repository.sha256_checksum:
            if await get_repository(redis, repository.software_uid):
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": f"Repository object with software_uid {repository.software_uid} already exists"
                    },
                )

            await create_repository(redis, repository)
            return repository

        return JSONResponse(
            status_code=404,
            content={"message": f"File object with url = {repository.url} is not found"},
        )

    @router.get("/repo/{software_uid}", response_model=Repository)
    async def get(self, software_uid: str, request: Request):
        redis = request.app.state.redis

        repo = await get_repository(redis, software_uid)
        if not repo:
            return JSONResponse(
                status_code=404,
                content={"message": f"Repository object with software_uid {software_uid} is not found"},
            )
        await increment_number_of_downloads(redis, software_uid)
        repo["number_of_downloads"] = int(repo["number_of_downloads"]) + 1
        return repo

    @router.patch("/repo/{software_uid}", response_model=Repository)
    async def patch(self, software_uid: str, repo_to_update: Repository, request: Request):
        redis = request.app.state.redis

        repo = await get_repository(redis, software_uid)
        if not repo:
            return JSONResponse(
                status_code=404,
                content={"message": f"Repository object with software_uid {software_uid} not found"},
            )
        updated_data = repo_to_update.dict(exclude_unset=True)

        return await patch_repository(redis, repo, updated_data)

    @router.delete("/repo/{software_uid}")
    async def delete(self, software_uid: str, request: Request):
        return JSONResponse(
            status_code=200,
            content={"message": "Mock for delete method"},
        )
