import asyncio
import contextlib
from pathlib import Path
from typing import Any

import docker

_SECCOMP_PATH = Path(__file__).parent.parent.parent / "config" / "seccomp.json"
MAX_OUTPUT_BYTES = 10_240  # 10 KB


def _seccomp_opt() -> list[str]:
    """Return security_opt list.

    On Linux the daemon reads the file path directly.
    On Windows Docker Desktop (WSL2 backend) absolute Windows paths can't be resolved
    by the daemon; fall back to no-new-privileges only rather than crashing.
    """
    import platform
    opts = ["no-new-privileges:true"]
    if platform.system() != "Windows" and _SECCOMP_PATH.exists():
        opts.append(f"seccomp={_SECCOMP_PATH}")
    return opts


async def run_validation_sandbox(command: str, timeout: int = 30) -> dict[str, Any]:
    """Run a command in a locked-down sandbox with zero network egress.

    Used by hook_validate dry-runs. Stricter limits than the production executor:
    - 128 MB RAM (vs 256 MB)
    - 25% CPU quota
    - 32 MB /tmp
    - pids_limit=32
    """
    client = docker.from_env()
    container = None
    result: dict[str, Any] = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "duration_ms": 0,
        "network_allowed": False,
        "success": False,
        "truncated": False,
    }

    try:
        container = client.containers.run(
            "alpine:3.19",
            command=["sh", "-c", command],
            environment={"DRY_RUN": "true", "HOOKCLI_MODE": "validate"},
            network_disabled=True,
            read_only=True,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},  # nosec B108
            security_opt=_seccomp_opt(),
            cap_drop=["ALL"],
            mem_limit="128m",
            nano_cpus=250_000_000,  # 0.25 vCPU
            pids_limit=32,
            detach=True,
        )

        loop = asyncio.get_running_loop()
        exit_data = await loop.run_in_executor(None, lambda: container.wait(timeout=timeout))
        result["exit_code"] = exit_data.get("StatusCode", -1)
        result["success"] = result["exit_code"] == 0

        raw = await loop.run_in_executor(None, lambda: container.logs(stdout=True, stderr=True))
        decoded = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else (raw or "")
        result["stdout"] = decoded[:MAX_OUTPUT_BYTES]
        result["truncated"] = len(decoded) > MAX_OUTPUT_BYTES

    except docker.errors.ContainerError as e:
        result["stderr"] = str(e)
    except Exception as e:
        result["stderr"] = str(e)
    finally:
        if container:
            with contextlib.suppress(Exception):
                container.remove(force=True)

    return result
