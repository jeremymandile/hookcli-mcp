import asyncio
import contextlib
import json
import time
from collections.abc import AsyncGenerator

import docker
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
task_registry: dict = {}

_HEARTBEAT_INTERVAL = 15  # seconds — keeps proxies and AI SSE clients alive
_QUEUE_MAX = 1000  # bounded queue — prevents memory exhaustion on noisy containers


@router.get("/{task_id}/stream")
async def stream_task_logs(task_id: str, request: Request):
    if task_id not in task_registry:
        raise HTTPException(status_code=404, detail="Task not found")
    task = task_registry[task_id]
    if task.get("status") != "running":
        raise HTTPException(status_code=400, detail=f"Task is {task.get('status')}")

    container_id = task["container_id"]
    client = docker.from_env()
    try:
        container = client.containers.get(container_id)
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Bounded queue prevents unbounded memory growth from a chatty container.
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
        stop_event = asyncio.Event()
        start_time = time.time()

        def docker_thread():
            try:
                for chunk in container.attach(stdout=True, stderr=True, stream=True, logs=True):
                    if stop_event.is_set():
                        break
                    try:
                        queue.put_nowait(chunk)
                    except asyncio.QueueFull:
                        # Drop oldest item to make room — prefer liveness over completeness
                        with contextlib.suppress(asyncio.QueueEmpty):
                            queue.get_nowait()
                        queue.put_nowait(chunk)
                queue.put_nowait(b"__EOF__")
            except Exception as e:
                queue.put_nowait(f"__ERROR__{str(e)}".encode())

        asyncio.create_task(asyncio.to_thread(docker_thread))

        buffer = b""

        try:
            while not request.is_disconnected():
                # Use a short get timeout so heartbeats fire even when the container is silent.
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except TimeoutError:
                    # No data within heartbeat window — send SSE comment to keep connection alive.
                    yield ": heartbeat\n\n"
                    continue

                if chunk == b"__EOF__":
                    container.reload()
                    exit_code = container.attrs["State"].get("ExitCode", -1)
                    duration_ms = int((time.time() - start_time) * 1000)
                    yield f"event: complete\ndata: {json.dumps({'exit_code': exit_code, 'duration_ms': duration_ms})}\n\n"
                    break

                if isinstance(chunk, bytes) and chunk.startswith(b"__ERROR__"):
                    yield f"event: error\ndata: {json.dumps({'error': chunk.decode().replace('__ERROR__', '')})}\n\n"
                    break

                buffer += chunk
                while len(buffer) >= 9:
                    stream_type = buffer[0]
                    length = int.from_bytes(buffer[1:9], byteorder="big")
                    if len(buffer) < 9 + length:
                        break
                    payload = buffer[9 : 9 + length].decode("utf-8", errors="replace").rstrip("\n")
                    buffer = buffer[9 + length :]
                    if payload:
                        event_name = "stdout" if stream_type == 1 else "stderr"
                        yield f"event: {event_name}\ndata: {payload}\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            stop_event.set()
            task["status"] = "completed"
            with contextlib.suppress(Exception):
                container.remove(force=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
