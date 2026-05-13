import pytest
import asyncio


@pytest.mark.asyncio
async def test_sse_frame_parsing():
    """Verify Docker frame parser correctly splits stdout/stderr."""
    frames = [
        b"\x01\x00\x00\x00\x00\x00\x00\x00\x0cstdout line 1",
        b"\x02\x00\x00\x00\x00\x00\x00\x00\tstderr msg",
    ]
    queue: asyncio.Queue = asyncio.Queue()
    for f in frames:
        await queue.put(f)
    await queue.put(b"__EOF__")

    buffer = b""
    events = []
    while True:
        chunk = await queue.get()
        if chunk == b"__EOF__":
            break
        buffer += chunk
        while len(buffer) >= 9:
            stream_type = buffer[0]
            length = int.from_bytes(buffer[1:9], byteorder="big")
            if len(buffer) < 9 + length:
                break
            payload = buffer[9:9 + length].decode("utf-8", errors="replace").rstrip("\n")
            buffer = buffer[9 + length:]
            if payload:
                event_name = "stdout" if stream_type == 1 else "stderr"
                events.append((event_name, payload))

    assert len(events) == 2
    assert events[0] == ("stdout", "stdout line 1")
    assert events[1] == ("stderr", "stderr msg")
