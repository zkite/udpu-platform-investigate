from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from config import get_app_settings
from .core import WireGuardManager

from .schemas import InterfaceStatus, Peer, PeerRemove

router = APIRouter()
settings = get_app_settings()


def get_wg() -> WireGuardManager:
    """Factory: one manager per request."""
    return WireGuardManager(
        interface=settings.WG_INTERFACE,
        sudo=True,
        auto_save=True,
    )


# ---------------------------------------------------------------------------
# Interface lifecycle
# ---------------------------------------------------------------------------

@router.get("/wireguard/status", response_model=InterfaceStatus)
def status(wg: WireGuardManager = Depends(get_wg)) -> InterfaceStatus:  # noqa: D401
    """Return current `wg0` active state."""
    return InterfaceStatus(interface=settings.WG_INTERFACE, active=str(wg.is_active()))


@router.post("/wireguard/up", response_class=JSONResponse)
def wg_up(wg: WireGuardManager = Depends(get_wg)):
    if wg.is_active():
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail="Interface already up")
    wg.up()
    return {"message": "Interface started"}


@router.post("/wireguard/down", response_class=JSONResponse)
def wg_down(wg: WireGuardManager = Depends(get_wg)):
    if not wg.is_active():
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail="Interface already down")
    wg.down()
    return {"message": "Interface stopped"}


# ---------------------------------------------------------------------------
# Peers
# ---------------------------------------------------------------------------

@router.get("/wireguard/peers")
def list_peers(wg: WireGuardManager = Depends(get_wg)):
    """Return peers converted to `Peer` schema."""
    try:
        return wg.list_peers()
    except Exception as exc:
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail=f"Failed to list peers: {exc}") from exc
    except Exception as exc:
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail=f"Failed to list peers: {exc}") from exc


@router.post("/wireguard/peer/add", status_code=HTTPStatus.OK, response_class=JSONResponse)
def add_peer(data: Peer, wg: WireGuardManager = Depends(get_wg)):
    try:
        wg.add_peer(
            public_key=data.public_key,
            allowed_ips=data.allowed_ips_str,
            endpoint=data.endpoint,
            persistent_keepalive=data.persistent_keepalive,
        )
        return {"message": "Peer created"}
    except Exception as exc:
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail=f"Failed to add peer: {exc}") from exc


@router.post("/wireguard/peer/remove", response_class=JSONResponse)
def remove_peer(data: PeerRemove, wg: WireGuardManager = Depends(get_wg)):
    try:
        wg.remove_peer(data.public_key)
        return {"message": f"Peer {data.public_key} removed"}
    except Exception as exc:
        raise HTTPException(HTTPStatus.BAD_REQUEST, detail=f"Failed to remove peer: {exc}") from exc

