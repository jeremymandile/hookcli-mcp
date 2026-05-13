import asyncio
import contextlib
from pathlib import Path
from typing import Any

import docker

_SECCOMP_PATH = Path(__file__).parent.parent.parent / "config" / "seccomp.json"
MAX_OUTPUT_BYTES = 10_240  # 10 KB — prevent memory exhaustion from verbose commands


def _seccomp_opt() -> list[str]:
    """Return security_opt list; skip custom seccomp on Windows (WSL2 daemon can't resolve Windows paths)."""
    import platform
    opts = ["no-new-privileges:true"]
    if platform.system() != "Windows" and _SECCOMP_PATH.exists():
        opts.append(f"seccomp={_SECCOMP_PATH}")
    return opts


async def run_in_sandbox(command: str, env: dict[str, str], hook_id: str, timeout: int = 120) -> dict[str, Any]:
    client = docker.from_env()
    container = None

    try:
        container = client.containers.run(
            "alpine:3.19",
            command=["sh", "-c", command],
            environment={**env, "DRY_RUN": "false"},
            network_disabled=True,  # zero egress — no outbound calls
            read_only=True,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},  # nosec B108
            security_opt=_seccomp_opt(),
            cap_drop=["ALL"],
            cap_add=["CHOWN", "SETUID", "SETGID"],
            mem_limit="256m",
            nano_cpus=500_000_000,  # 0.5 vCPU
            pids_limit=64,  # fork-bomb prevention
            detach=True,
            labels={"hookcli.hook_id": hook_id},
        )

        loop = asyncio.get_running_loop()
        exit_data = await loop.run_in_executor(None, lambda: container.wait(timeout=timeout))
        exit_code = exit_data.get("StatusCode", -1)

        raw_logs = await loop.run_in_executor(None, lambda: container.logs(stdout=True, stderr=True))
        # Truncate to prevent callers accumulating unbounded output
        decoded = raw_logs.decode("utf-8", errors="replace") if isinstance(raw_logs, bytes) else raw_logs
        output = decoded[:MAX_OUTPUT_BYTES]
        truncated = len(decoded) > MAX_OUTPUT_BYTES

        return {
            "exit_code": exit_code,
            "stdout": output,
            "stderr": "",
            "success": exit_code == 0,
            "truncated": truncated,
        }
    except docker.errors.APIError as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False, "truncated": False}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False, "truncated": False}
    finally:
        if container:
            with contextlib.suppress(Exception):
                container.remove(force=True)
