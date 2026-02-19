import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from redis.asyncio.client import Redis
from starlette.websockets import WebSocketState

from domain.api.jobs.core import JobRepository
from domain.api.jobs.schemas import JobSchema
from domain.api.northbound.dependencies import get_udpu_status
from domain.api.jobs.queues.core import QueueRepository
from services.logging.logger import log as logger
from services.redis.exceptions import RedisResponseError


ws_router = APIRouter()

def _to_str(x):
    """Convert bytes or bytearray to str. Return the value unchanged otherwise."""
    return x.decode() if isinstance(x, (bytes, bytearray)) else x

def _normalize_map(m):
    """Return a dict with str keys and str values. Decode bytes where needed."""
    return {_to_str(k): _to_str(v) for k, v in m.items()}


@ws_router.websocket("/pubsub")
async def pubsub_endpoint(
    websocket: WebSocket,
    channel: str = Query(..., description="Channel name for pubsub"),
) -> None:
    """
    Agent-facing WebSocket.

    - Reads entries from the client's personal stream and sends them to the WebSocket.
    - Receives text from the WebSocket and writes it to the server:<client> stream.
    """
    await websocket.accept()
    redis: Redis = websocket.app.state.redis
    client = channel

    # Personal stream where the server publishes commands for this client.
    client_stream = client

    async def deliver() -> None:
        """Read from the client's personal stream and send to the WebSocket. XREAD + XDEL."""
        last_id = "0-0"
        while True:
            try:
                resp = await redis.xread(streams={client_stream: last_id}, count=1, block=1000)
                if not resp:
                    continue
                _, messages = resp[0]
                for msg_id, raw in messages:
                    data = _normalize_map(raw)
                    await websocket.send_json(data)
                    # Delete the processed entry from the client's stream.
                    try:
                        await redis.xdel(client_stream, msg_id)
                    except Exception as e:
                        logger.error("XDEL pubsub failed for %s", msg_id, exc_info=e)
                    last_id = msg_id
            except (asyncio.CancelledError, WebSocketDisconnect):
                break
            except Exception as e:
                logger.error("Delivery error", exc_info=e)
                await asyncio.sleep(1)

    async def receive() -> None:
        """Receive text from the WebSocket and write it to the server:<client> stream."""
        server_stream = f"server:{client}"
        while True:
            try:
                text = await websocket.receive_text()
                # Normalize newlines and collapse whitespace.
                text = text.replace("\r", " ").replace("\n", " ")
                text = " ".join(text.split())
                # Keep only the latest message in the server stream.
                await redis.xadd(
                    server_stream,
                    {"message": text},
                    maxlen=1,
                    approximate=False,
                )
            except (asyncio.CancelledError, WebSocketDisconnect):
                break
            except Exception as e:
                logger.error("Receive error", exc_info=e)
                break

    try:
        # Run producer and consumer concurrently for this WebSocket connection.
        async with asyncio.TaskGroup() as tg:
            tg.create_task(deliver(), name=f"deliver:{client}")
            tg.create_task(receive(), name=f"receive:{client}")
    except* Exception as eg:
        for e in eg.exceptions:
            logger.error("Websocket task failed", exc_info=e)
    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()


@ws_router.websocket("/pub")
async def pub_endpoint(
    websocket: WebSocket,
    channel: str = Query(..., description="Channel name for pub commands"),
) -> None:
    """
    UI-facing WebSocket.

    - Receives commands from the UI and publishes tasks to the client's personal stream.
    - Subscribes to server:<client>, sends incoming messages to the UI, then deletes them.
    """
    await websocket.accept()
    redis: Redis = websocket.app.state.redis
    client = channel

    # Personal incoming stream from this client to the server.
    server_stream = f"server:{client}"
    job_repo = JobRepository(redis)
    queue_repo = QueueRepository(redis)
    shutdown_event = asyncio.Event()

    async def publisher() -> None:
        """Read commands from the WebSocket and push tasks into the client's personal stream."""
        stream = client
        while True:
            try:
                cmd = await websocket.receive_text()

                if cmd.startswith("run queue"):
                    _, qid = cmd.split("run queue", 1)
                    qid = qid.strip()
                    try:
                        queue = await queue_repo.get(qid)
                    except RedisResponseError as e:
                        logger.error("Failed to fetch queue %s: %s", qid, e)
                        await websocket.send_text(f"Error fetching queue: {qid}")
                        continue
                    if queue:
                        await redis.xadd(
                            stream,
                            {
                                "action_type": "queue",
                                "name": queue.name,
                                "jobs": queue.queue,
                                "locked": queue.locked,
                            },
                            maxlen=10000,
                            approximate=True,
                        )
                    else:
                        await websocket.send_text(f"No such queue: {qid}")

                elif cmd.startswith("run job"):
                    if "status" in cmd:
                        obj = await get_udpu_status(redis, client)
                        if obj:
                            await websocket.send_json({"state": obj.state, "status": obj.status})
                        else:
                            await websocket.send_text(f"Error fetching udpu status: {client}")
                        continue

                    _, jid = cmd.split("run job", 1)
                    jid = jid.strip()
                    try:
                        job: JobSchema = await job_repo.get(jid)
                    except RedisResponseError as e:
                        logger.error("Failed to fetch job %s: %s", jid, e)
                        await websocket.send_text(f"Error fetching job: {jid}")
                        continue

                    if not job:
                        await websocket.send_text(f"No such job: {jid}")
                        continue

                    await redis.xadd(
                        stream,
                        {
                            "action_type": "job",
                            "command": job.command,
                            "frequency": job.frequency.value if job.frequency else "once",
                            "require_output": str(job.require_output).lower(),
                            "name": job.name,
                            "locked": str(job.locked).lower(),
                            "required_software": job.required_software,
                            "type": job.type,
                            "vbuser_id": job.vbuser_id,
                        },
                        maxlen=10000,
                        approximate=True,
                    )

            except (asyncio.CancelledError, WebSocketDisconnect):
                shutdown_event.set()
                break
            except Exception as e:
                logger.error("Publisher error", exc_info=e)
                shutdown_event.set()
                break
        shutdown_event.set()

    async def subscriber() -> None:
        """Read one message from server:<client>, send it to the WebSocket, then delete it."""
        last_id = "0-0"
        while True:
            if shutdown_event.is_set():
                break
            try:
                resp = await redis.xread(streams={server_stream: last_id}, count=1, block=1000)
                if shutdown_event.is_set():
                    break
                if not resp:
                    continue

                _, messages = resp[0]
                for msg_id, raw in messages:
                    data = _normalize_map(raw)
                    text = data.get("message")
                    if text is not None:
                        if shutdown_event.is_set() or websocket.application_state != WebSocketState.CONNECTED or websocket.client_state != WebSocketState.CONNECTED:
                            break
                        await websocket.send_text(text)
                    try:
                        await redis.xdel(server_stream, msg_id)
                    except Exception as e:
                        logger.error("XDEL server failed for %s", msg_id, exc_info=e)
                    last_id = msg_id

            except (asyncio.CancelledError, WebSocketDisconnect):
                shutdown_event.set()
                break
            except Exception as e:
                if shutdown_event.is_set() or websocket.application_state != WebSocketState.CONNECTED or websocket.client_state != WebSocketState.CONNECTED:
                    break
                if isinstance(e, RuntimeError):
                    break
                logger.error("Subscriber error", exc_info=e)
                await asyncio.sleep(0.5)

    try:
        # Run command publisher and server subscriber concurrently.
        async with asyncio.TaskGroup() as tg:
            tg.create_task(publisher(), name=f"pub:{client}")
            tg.create_task(subscriber(), name=f"sub:{client}")
    except* Exception as eg:
        for e in eg.exceptions:
            logger.error("Websocket task failed", exc_info=e)
    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
