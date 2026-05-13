import asyncio
import docker
from pathlib import Path
from typing import Dict, Any

SECCOMP_PATH = Path(__file__).parent.parent.parent / "config" / "seccomp.json"
MAX_OUTPUT_BYTES = 10_240  # 10 KB


async def run_validation_sandbox(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Run a command in a locked-down sandbox with zero network egress.

    Used by hook_validate dry-runs. Stricter limits than the production executor:
    - 128 MB RAM (vs 256 MB)
    - 25% CPU quota
    - 32 MB /tmp
    - pids_limit=32
    """
    client = docker.from_env()
    container = None
    result: Dict[str, Any] = {
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
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},
            security_opt=["no-new-privileges:true", f"seccomp={SECCOMP_PATH}"],
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
            try:
                container.remove(force=True)
            except Exception:
                pass

    return result
