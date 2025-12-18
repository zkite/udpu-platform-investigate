from asyncio import gather
from fastapi import Request, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic
from fastapi_utils.cbv import cbv
from services.logging.logger import log as logger
from http import HTTPStatus as status

from config import get_app_settings
from domain.api.roles.dependencies import get_udpu_role
from domain.api.vbuser.dependencies import location_exist

from .constants import UDPU_ENTITY, CONTEXT_KEY_PREFIX, LOCATION_PREFIX, STATUS_PREFIX
from .dependencies import (
    bulk_update_udpu,
    create_udpu,
    update_udpu,
    delete_udpu,
    get_subscriber_key_by_mac_addr,
    get_subscribers_by_location,
    get_udpu,
    get_udpu_location_list,
    is_unique_hostname,
    is_unique_mac_address,
    is_valid_hostname,
    is_valid_mac_address,
    map_mac_address_to_subscriber,
    update_udpu_list,
    generate_client_ip,
    get_public_key,
    get_udpu_status,
    create_udpu_status,
)
from .exceptions import RedisResponseError
from .schemas import Udpu, UdpuUpdate, UnregisteredDevice, UdpuStatus

from domain.api.vbuser.constants import GHN_PROFILE
from domain.api.vbuser.schemas import VBUser
from domain.api.vbuser.dependencies import create_vbuser, get_vbuser_by_udpu, delete_vbuser
from domain.api.vbce.schemas import Vbce
from domain.api.vbce.dependencies import (
    get_vbce_by_location_id, find_empty_vbce, update_vbce_location_list
)


settings = get_app_settings()
router = APIRouter()
security = HTTPBasic()


@cbv(router)
class UdpuActivation:
    settings = get_app_settings()

    @router.post("/udpu")
    async def post(self, udpu: Udpu, request: Request):
        """
        Create a new UDPU record and provision Wireguard tunnel.
        """
        redis = request.app.state.redis

        if udpu.mac_address and not is_valid_mac_address(udpu.mac_address):
            return JSONResponse(status_code=400, content={"message": f"Mac address {udpu.mac_address} is not valid"})
        if not is_valid_hostname(udpu.hostname):
            return JSONResponse(status_code=400, content={"message": f"Hostname {udpu.hostname} is not valid"})

        try:
            client_ip = await generate_client_ip(redis)
            udpu.wg_client_ip = client_ip
            udpu.wg_server_ip = settings.WG_SERVER_IP
            udpu.wg_server_port = settings.WG_SERVER_PORT

            # Extract server address without mask and convert to /32
            server_ip_only = settings.WG_SERVER_IP.split("/")[0]
            server_ip32 = f"{server_ip_only}/32"

            # Combine server IP/32 with all routes from settings.WG_ROUTES
            udpu.wg_allowed_ips = server_ip32 + "," + settings.WG_ROUTES

            udpu.wg_routes = settings.WG_ROUTES
            udpu.endpoint = self.settings.server_host
            udpu.wg_server_public_key = get_public_key()
        except Exception as e:
            return JSONResponse(status_code=500, content={"message": str(e)})

        role = await get_udpu_role(redis, udpu.role)
        if not role:
            return JSONResponse(status_code=400, content={"message": f"Role name {udpu.role} not found"})

        if await get_udpu(redis, udpu.subscriber_uid):
            return JSONResponse(
                status_code=400,
                content={"message": f"Udpu with subscriber_uid {udpu.subscriber_uid} already exists"},
            )

        if udpu.mac_address and not (await is_unique_mac_address(redis, udpu.mac_address)):
            return JSONResponse(status_code=400, content={"message": f"Mac address {udpu.mac_address} already exists"})

        if not (await is_unique_hostname(redis, udpu.hostname)):
            return JSONResponse(status_code=400, content={"message": f"Hostname {udpu.hostname} already exists"})

        vbce = await get_vbce_by_location_id(redis, udpu.location)

        try:
            ghn_interface = role["interfaces"]["ghn_ports"]["port_1"]["ghn_interface"]
            lcmp_interface = role["interfaces"]["ghn_ports"]["port_1"]["lcmp_interface"]
        except Exception:
            try:
                ghn_interface = role["interfaces"]["ghn_ports"][0]["ghn_interface"]
                lcmp_interface = role["interfaces"]["ghn_ports"][1]["lcmp_interface"]
            except Exception:
                ghn_interface = ""
                lcmp_interface = ""

        try:
            if vbce:
                max_users = int(vbce["max_users"])
                current_users = int(vbce["current_users"])
                if current_users >= max_users:
                    return JSONResponse(status_code=400,
                                        content={"message": "The allowed number of users has been exceeded."})
                vbuser = VBUser(
                    udpu=udpu.subscriber_uid,
                    location_id=udpu.location,
                    ghn_interface=ghn_interface,
                    lcmp_interface=lcmp_interface,
                    force_local="false",
                    ghn_profile=GHN_PROFILE,
                    conf_ghn_profile=GHN_PROFILE,
                )
                await create_vbuser(redis, vbuser)
            else:
                empty_vbce = await find_empty_vbce(redis)
                if empty_vbce:
                    vbce_to_update = empty_vbce
                    vbce_to_update["location_id"] = udpu.location
                    await redis.hset(vbce_to_update["key"], mapping=vbce_to_update)
                    await redis.set(vbce_to_update["location_id"], vbce_to_update["name"])
                    await update_vbce_location_list(redis, vbce_to_update["location_id"])
                    vbuser = VBUser(
                        udpu=udpu.subscriber_uid,
                        location_id=udpu.location,
                        ghn_interface=ghn_interface,
                        lcmp_interface=lcmp_interface,
                        force_local="false",
                        ghn_profile=GHN_PROFILE,
                        conf_ghn_profile=GHN_PROFILE,
                    )
                    await create_vbuser(redis, vbuser)
                else:
                    return JSONResponse(status_code=400,
                                        content={"message": f"No available vbce found for location {udpu.location}"})

            await gather(
                create_udpu(redis, udpu),
                update_udpu_list(redis, f"{UDPU_ENTITY}:mac_address_list", udpu.mac_address),
                update_udpu_list(redis, f"{UDPU_ENTITY}:hostname_list", udpu.hostname),
                update_udpu_list(redis, f"{UDPU_ENTITY}:location_list", udpu.location),
                update_udpu_list(redis, f"{LOCATION_PREFIX}:{udpu.location}", udpu.subscriber_uid),
                map_mac_address_to_subscriber(redis, udpu.mac_address_key, udpu.subscriber_key),
            )

            udpu_obj = await get_udpu(redis, udpu.subscriber_key)
            return JSONResponse(status_code=200, content=udpu_obj)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.get("/udpu/locations")
    async def get_udpu_locations(self, request: Request):
        redis = request.app.state.redis
        try:
            locations = await get_udpu_location_list(redis)
            return JSONResponse(status_code=200, content=list(locations))
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.get("/{location_id}/udpu_list")
    async def get_udpu_list_by_location(self, location_id: str, request: Request):
        redis = request.app.state.redis
        try:
            subscriber_uids = await get_subscribers_by_location(redis, location_id)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

        if not subscriber_uids:
            return JSONResponse(
                status_code=404,
                content={"message": f"Udpu objects with location id '{location_id}' not found"}
            )

        udpu_list_by_location = []
        for s_uid in subscriber_uids:
            udpu_obj = await get_udpu(redis, s_uid)
            if udpu_obj:
                udpu_list_by_location.append(udpu_obj)

        return JSONResponse(status_code=200, content=udpu_list_by_location)

    @router.put("/udpu_bulk/{location_id}")
    async def update_udpu_bulk_by_location(self, update_request: UdpuUpdate, location_id: str, request: Request):
        redis = request.app.state.redis
        try:
            subscriber_uids = await get_subscribers_by_location(redis, location_id)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

        if not subscriber_uids:
            return JSONResponse(
                status_code=404,
                content={"message": f"Udpu objects with location id '{location_id}' not found"}
            )

        if not await get_udpu_role(redis, update_request.role):
            return JSONResponse(status_code=400, content={"message": f"Role name {update_request.role} not found"})

        udpu_lst = []
        for subscriber_uid in subscriber_uids:
            udpu_obj = await get_udpu(redis, subscriber_uid)
            if udpu_obj:
                udpu_lst.append(udpu_obj)

        try:
            updated = await bulk_update_udpu(redis, udpu_lst, update_request)
            return JSONResponse(status_code=200, content=updated)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.get("/subscriber/{subscriber_uid:path}/udpu")
    async def get_by_subscriber_uid(self, request: Request, subscriber_uid: str):
        redis = request.app.state.redis
        try:
            udpu_obj = await get_udpu(redis, subscriber_uid)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

        if not udpu_obj:
            return JSONResponse(status_code=404, content={"message": f"Udpu object with subscriber_uid {subscriber_uid} not found"})

        return JSONResponse(status_code=200, content=udpu_obj)

    @router.get("/adapter/{mac_address}/udpu")
    async def get_by_mac_address(self, request: Request, mac_address: str, subscriber: str = "none"):
        logger.info(f"get_by_mac_address | client ip: {request.client.host}")
        logger.info(f"get_by_mac_address | subscriber: {request.client.host}")

        redis = request.app.state.redis

        if not mac_address:
            return JSONResponse(status_code=400, content={"message": "Mac address should be provided"})
        if not is_valid_mac_address(mac_address):
            return JSONResponse(status_code=400, content={"message": f"Mac address {mac_address} is not valid"})

        subscriber_key = await get_subscriber_key_by_mac_addr(redis, mac_address)
        if not subscriber_key or not subscriber_key.startswith(f"{UDPU_ENTITY}:"):
            udpu_obj = await get_udpu(redis, subscriber)
            if not udpu_obj:
                    default_udpu = Udpu(
                        location="default",
                        mac_address="00:00:00:00:00:00",
                        role="default",
                        upstream_qos="",
                        downstream_qos=""
                    )
                    await create_udpu(redis, default_udpu)
                    udpu_obj = await get_udpu(redis, default_udpu.subscriber_uid)

                    # un_registered LED
                    await redis.xadd(udpu_obj['subscriber_uid'], {
                        "action_type": "job",
                        #"command": "echo UN_REGISTERED",
                        "command": "echo 1 > /sys/class/leds/udpu:red:network/brightness && echo 0 > /sys/class/leds/udpu:green:network/brightness",
                        "frequency": "once",
                        "require_output": "false",
                        "name": "un_registered_device",
                        "locked": "false",
                        "required_software": ""
                    })
                    await redis.set(f"unregistered:{udpu_obj['subscriber_uid']}", 1)

                    return JSONResponse(status_code=200, content=udpu_obj)
            else:
                return JSONResponse(status_code=200, content=udpu_obj)

        subscriber_uid = subscriber_key.split(f"{UDPU_ENTITY}:")[1]
        udpu_obj = await get_udpu(redis, subscriber_uid)

        # registered LED
        await redis.set(f"unregistered:{udpu_obj['subscriber_uid']}", 0)
        await redis.xadd(udpu_obj['subscriber_uid'], {
            "action_type": "job",
            #"command": "echo REGISTERED",
            "command": "echo 0 > /sys/class/leds/udpu:red:network/brightness && echo 1 > /sys/class/leds/udpu:green:network/brightness",
            "frequency": "once",
            "require_output": "false",
            "name": "registered_device",
            "locked": "false",
            "required_software": ""
        })

        return JSONResponse(status_code=200, content=udpu_obj)

    @router.put("/subscriber/{subscriber_uid:path}/udpu")
    async def put(self, request: Request, update_request: UdpuUpdate, subscriber_uid: str):
        redis = request.app.state.redis
        try:
            udpu_obj = await get_udpu(redis, subscriber_uid)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

        if not udpu_obj:
            return JSONResponse(status_code=404, content={"message": f"Udpu object with subscriber_uid {subscriber_uid} not found"})

        if update_request.mac_address and not is_valid_mac_address(update_request.mac_address):
            return JSONResponse(status_code=400, content={"message": f"Mac address {update_request.mac_address} is not valid"})

        if not await get_udpu_role(redis, update_request.role):
            return JSONResponse(status_code=400, content={"message": f"Role name {update_request.role} not found"})

        if udpu_obj["location"] != update_request.location:
            if update_request.location and not (await location_exist(redis, update_request.location)):
                if not await find_empty_vbce(redis):
                    return JSONResponse(
                        status_code=400,
                        content={"message": f"No available vbce found for location {update_request.location}"}
                    )

        role = await get_udpu_role(redis, update_request.role)
        if not role:
            return JSONResponse(status_code=400, content={"message": f"Role name {udpu_obj['role']} not found"})

        vbce = await get_vbce_by_location_id(redis, update_request.location)
        if vbce:
            max_users = int(vbce["max_users"])
            current_users = int(vbce["current_users"])
            if current_users >= max_users:
                return JSONResponse(status_code=400, content={"message": "The allowed number of users has been exceeded."})
        else:
            empty_vbce = await find_empty_vbce(redis)
            if empty_vbce:
                vbce_to_update = Vbce(**empty_vbce)
                vbce_to_update.location_id = update_request.location
                await redis.hset(vbce_to_update.key, mapping=vbce_to_update.dict())
                await redis.set(vbce_to_update.location_id, vbce_to_update.name)
                await update_vbce_location_list(redis, vbce_to_update.location_id)
            else:
                return JSONResponse(
                    status_code=400,
                    content={"message": f"No available vbce found for location {update_request.location}"}
                )

        try:
            try:
                ghn_interface = role["interfaces"]["ghn_ports"]["port_1"]["ghn_interface"]
                lcmp_interface = role["interfaces"]["ghn_ports"]["port_1"]["lcmp_interface"]
            except Exception:
                try:
                    ghn_interface = role["interfaces"]["ghn_ports"][0]["ghn_interface"]
                    lcmp_interface = role["interfaces"]["ghn_ports"][1]["lcmp_interface"]
                except Exception:
                    ghn_interface = ""
                    lcmp_interface = ""

            updated_udpu = await update_udpu(redis, update_request, udpu_obj)
            old_vbuser = await get_vbuser_by_udpu(redis, udpu_obj["subscriber_uid"])
            if old_vbuser:
                await delete_vbuser(redis, old_vbuser["vb_uid"], old_vbuser["location_id"], old_vbuser["seed_idx"])
            vbuser = VBUser(
                udpu=updated_udpu["subscriber_uid"],
                location_id=update_request.location,
                ghn_interface=ghn_interface,
                lcmp_interface=lcmp_interface,
                force_local="false",
                ghn_profile=GHN_PROFILE,
                conf_ghn_profile=GHN_PROFILE,
            )
            await create_vbuser(redis, vbuser)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

        return JSONResponse(status_code=200, content=updated_udpu)

    @router.put("/adapter/{mac_address}/udpu")
    async def put_by_mac_address(self, request: Request, update_request: Udpu, mac_address: str):
        redis = request.app.state.redis
        subscriber_key = await get_subscriber_key_by_mac_addr(redis, mac_address)
        if not is_valid_mac_address(update_request.mac_address):
            return JSONResponse(status_code=400, content={"message": f"Mac address {update_request.mac_address} is not valid"})
        if not await get_udpu_role(redis, update_request.role):
            return JSONResponse(status_code=400, content={"message": f"Role name {update_request.role} not found"})
        if not subscriber_key or not subscriber_key.startswith(f"{UDPU_ENTITY}:"):
            return JSONResponse(status_code=404, content={"message": f"Udpu object with mac_address {mac_address} not found"})
        subscriber_uid = subscriber_key.split(f"{UDPU_ENTITY}:")[1]
        try:
            udpu_obj = await get_udpu(redis, subscriber_uid)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})
        if not udpu_obj:
            return JSONResponse(status_code=404, content={"message": f"Udpu object with mac_address {mac_address} not found"})
        old_mac_address = udpu_obj["mac_address"]
        if udpu_obj["location"] != update_request.location:
            if update_request.location and not (await location_exist(redis, update_request.location)):
                if not await find_empty_vbce(redis):
                    return JSONResponse(status_code=400, content={"message": f"No available vbce found for location {update_request.location}"})
        role = await get_udpu_role(redis, udpu_obj["role"])
        if not role:
            return JSONResponse(status_code=400, content={"message": f"Role name {udpu_obj['role']} not found"})
        vbce = await get_vbce_by_location_id(redis, update_request.location)
        if vbce:
            max_users = int(vbce["max_users"])
            current_users = int(vbce["current_users"])
            if current_users >= max_users:
                return JSONResponse(status_code=400, content={"message": "The allowed number of users has been exceeded."})
        else:
            empty_vbce = await find_empty_vbce(redis)
            if empty_vbce:
                vbce_to_update = Vbce(**empty_vbce)
                vbce_to_update.location_id = update_request.location
                await redis.hset(vbce_to_update.key, mapping=vbce_to_update.dict())
                await redis.set(vbce_to_update.location_id, vbce_to_update.name)
                await update_vbce_location_list(redis, vbce_to_update.location_id)
            else:
                return JSONResponse(status_code=400, content={"message": f"No available vbce found for location {update_request.location}"})
        try:
            updated_udpu = await update_udpu(redis, update_request, udpu_obj)
            old_vbuser = await get_vbuser_by_udpu(redis, udpu_obj["subscriber_uid"])
            await delete_vbuser(redis, old_vbuser["vb_uid"], old_vbuser["location_id"], old_vbuser["seed_idx"])
            try:
                ghn_interface = role["interfaces"]["ghn_ports"]["port_1"]["ghn_interface"]
                lcmp_interface = role["interfaces"]["port_1"]["lcmp_interface"]
            except Exception:
                try:
                    ghn_interface = role["interfaces"]["ghn_ports"][0]["ghn_interface"]
                    lcmp_interface = role["interfaces"]["ghn_ports"][1]["lcmp_interface"]
                except Exception:
                    ghn_interface = ""
                    lcmp_interface = ""
            vbuser = VBUser(
                udpu=updated_udpu["subscriber_uid"],
                location_id=update_request.location,
                ghn_interface=ghn_interface,
                lcmp_interface=lcmp_interface,
                force_local="false",
                ghn_profile=GHN_PROFILE,
                conf_ghn_profile=GHN_PROFILE,
            )
            await create_vbuser(redis, vbuser)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})
        return JSONResponse(status_code=200, content=updated_udpu)

    @router.delete("/subscriber/{subscriber_uid:path}/udpu")
    async def delete(self, subscriber_uid: str, request: Request):
        redis = request.app.state.redis
        try:
            udpu_obj = await get_udpu(redis, subscriber_uid)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})
        if not udpu_obj:
            return JSONResponse(status_code=404, content={"message": f"Udpu object with subscriber_uid {subscriber_uid} not found"})
        try:
            await delete_udpu(redis, udpu_obj)
            vbuser = await get_vbuser_by_udpu(redis, subscriber_uid)
            if vbuser:
                await delete_vbuser(redis, vbuser["vb_uid"], vbuser["location_id"], vbuser["seed_idx"])
            return JSONResponse(
                status_code=200,
                content={"message": f"Udpu object with subscriber_uid {subscriber_uid} removed successfully"},
            )
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.delete("/adapter/{mac_address}/udpu")
    async def delete_by_mac_address(self, request: Request, mac_address: str):
        if not mac_address:
            return JSONResponse(status_code=400, content={"message": "Mac address should be provided"})
        redis = request.app.state.redis
        subscriber_key = await get_subscriber_key_by_mac_addr(redis, mac_address)
        if not is_valid_mac_address(mac_address):
            return JSONResponse(status_code=400, content={"message": f"Mac address {mac_address} is not valid"})
        if not subscriber_key or not subscriber_key.startswith(f"{UDPU_ENTITY}:"):
            return JSONResponse(status_code=404, content={"message": f"Udpu object with mac_address {mac_address} not found"})
        subscriber_uid = subscriber_key.split(f"{UDPU_ENTITY}:")[1]
        try:
            udpu_obj = await get_udpu(redis, subscriber_uid)
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})
        if not udpu_obj:
            return JSONResponse(status_code=404, content={"message": f"Udpu object with mac_address {mac_address} not found"})
        try:
            await delete_udpu(redis, udpu_obj)
            vbuser = await get_vbuser_by_udpu(redis, subscriber_uid)
            if vbuser:
                await delete_vbuser(redis, vbuser["vb_uid"], vbuser["location_id"], vbuser["seed_idx"])
            return JSONResponse(
                status_code=200,
                content={"message": f"Udpu object with mac_address {mac_address} removed successfully"},
            )
        except RedisResponseError as e:
            return JSONResponse(status_code=500, content={"message": e.message})

    @router.post("/unregistered_device")
    async def add_unregistered_device(self, device: UnregisteredDevice, request: Request):
        redis = request.app.state.redis
        key = f"unregistered:{device.ip_address}"
        device_data = {
            "subscriber_uid": device.subscriber_uid,
            "last_call_home_dt": device.last_call_home_dt,
            "ip_address": device.ip_address
        }
        await redis.hset(key, mapping=device_data)
        return JSONResponse(status_code=200, content={"message": "Device added successfully"})

    @router.get("/unregistered_devices")
    async def get_unregistered_devices(self, request: Request):
        redis = request.app.state.redis
        devices = []
        async for key in redis.scan_iter(match="unregistered:*"):
            device_data = await redis.hgetall(key)
            devices.append(device_data)
        return JSONResponse(status_code=200, content=devices)

    @router.get("/udpu/{subscriber_uid}/status")
    async def udpu_status(self, request: Request, subscriber_uid: str):
        redis = request.app.state.redis
        try:
            obj = await get_udpu_status(redis, subscriber_uid)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"Redis error: {e}")
        if obj is None:
            raise HTTPException(status_code=404, detail="Status not found")
        return {"state": obj.state, "status": obj.status}

    @router.post("/udpu/status", response_model=UdpuStatus)
    async def post_udpu_status(self, request: Request, payload: UdpuStatus):
        redis = request.app.state.redis

        logger.info(f"post_udpu_status | {payload}")

        data = UdpuStatus(**payload.model_dump())

        udpu = await get_udpu(redis, data.subscriber_uid)

        if udpu["mac_address"] != "00:00:00:00:00:00":
            data.state = "registered"
        else:
            data.state = "not_registered"

        try:
            await create_udpu_status(redis, data)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=f"Redis error: {e}")

        return data

    @router.get("/udpu/status", status_code=status.OK)
    async def list_udpu_statuses(self, request: Request):
        redis = request.app.state.redis
        results = []

        try:
            async for key in redis.scan_iter(match=f"{STATUS_PREFIX}:*", count=100):
                try:
                    _, subscriber_uid = key.split(":", 1)
                except ValueError:
                    continue

                data = await redis.hgetall(key)
                if not data:
                    continue

                status_data = await get_udpu_status(redis, subscriber_uid)
                results.append({
                        "subscriber_uid": status_data.subscriber_uid,
                        "state": status_data.state,
                        "status": status_data.status,
                    })
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")