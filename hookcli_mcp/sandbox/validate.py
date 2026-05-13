import asyncio
import docker
from pathlib import Path
from typing import Dict, Any

SECCOMP_PATH = Path(__file__).parent.parent.parent / "config" / "seccomp.json"


async def run_validation_sandbox(command: str, timeout: int = 30) -> Dict[str, Any]:
    client = docker.from_env()
    container = None
    result: Dict[str, Any] = {
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "duration_ms": 0,
        "network_allowed": False,
        "success": False,
    }

    try:
        container = client.containers.run(
            "alpine:3.19",
            command=["sh", "-c", command],
            environment={"DRY_RUN": "true", "HOOKCLI_MODE": "validate"},
            network_mode="none",
            read_only=True,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},
            security_opt=["no-new-privileges:true", f"seccomp={SECCOMP_PATH}"],
            cap_drop=["ALL"],
            mem_limit="128m",
            cpu_quota=25000,
            detach=True,
        )

        loop = asyncio.get_running_loop()
        exit_data = await loop.run_in_executor(None, lambda: container.wait(timeout=timeout))
        result["exit_code"] = exit_data.get("StatusCode", -1)
        result["success"] = result["exit_code"] == 0

        stdout = await loop.run_in_executor(None, lambda: container.logs(stdout=True, stderr=False))
        stderr = await loop.run_in_executor(None, lambda: container.logs(stdout=False, stderr=True))
        result["stdout"] = stdout.decode().strip() if isinstance(stdout, bytes) else ""
        result["stderr"] = stderr.decode().strip() if isinstance(stderr, bytes) else ""

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
