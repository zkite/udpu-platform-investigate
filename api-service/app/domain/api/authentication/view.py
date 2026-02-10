from typing import List

from fastapi import APIRouter
from fastapi_utils.cbv import cbv

from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
from domain.api.authentication.core import StampService
from domain.api.authentication.dependencies import get_stamp_service
from domain.api.authentication.schemas import Stamp

router = APIRouter()


@cbv(router)
class Stamps:
    @router.post("/stamps", status_code=status.HTTP_201_CREATED)
    async def post(
        self,
        stamp: Stamp,
        service: StampService = Depends(get_stamp_service),
    ):
        """
        Create a new stamp entry.
        """
        try:
            await service.create(stamp)
        except ValueError as ve:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(ve),
            )
        return JSONResponse(
            content={"message": "Stamp created"},
            status_code=status.HTTP_201_CREATED,
        )

    @router.get("/stamps", response_model=List[Stamp], status_code=status.HTTP_200_OK)
    async def get_list(
        self,
        service: StampService = Depends(get_stamp_service),
    ):
        """
        List all stamps.
        """
        data = await service.list_all()
        return [Stamp(mac_address=mac, body=body) for mac, body in data.items()]

    @router.get("/stamps/{mac_address}", response_model=Stamp, status_code=status.HTTP_200_OK)
    async def get_stamp(
        self,
        mac_address: str,
        service: StampService = Depends(get_stamp_service),
    ):
        """
        Retrieve a stamp by MAC address.
        """
        body = await service.get(mac_address)
        if body is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stamp for MAC {mac_address} not found",
            )
        return Stamp(mac_address=mac_address, body=body)

    @router.delete("/stamps/{mac_address}", status_code=status.HTTP_200_OK)
    async def delete_stamp(
        self,
        mac_address: str,
        service: StampService = Depends(get_stamp_service),
    ):
        """
        Delete a stamp by MAC address.
        """
        existing = await service.get(mac_address)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stamp for MAC {mac_address} not found",
            )
        await service.delete(mac_address)
        return JSONResponse(
            content={"message": f"Stamp {mac_address} deleted"},
            status_code=status.HTTP_200_OK,
        )
