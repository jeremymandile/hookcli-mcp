import asyncio
import docker
from pathlib import Path
from typing import Dict, Any

SECCOMP_PATH = Path(__file__).parent.parent.parent / "config" / "seccomp.json"


async def run_in_sandbox(command: str, env: Dict[str, str], hook_id: str, timeout: int = 120) -> Dict[str, Any]:
    client = docker.from_env()
    container = None

    try:
        container = client.containers.run(
            "alpine:3.19",
            command=["sh", "-c", command],
            environment=env,
            read_only=True,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
            security_opt=["no-new-privileges:true", f"seccomp={SECCOMP_PATH}"],
            cap_drop=["ALL"],
            cap_add=["CHOWN", "SETUID", "SETGID"],
            network="hook-isolated",
            mem_limit="256m",
            cpu_period=100000,
            cpu_quota=50000,
            detach=True,
        )

        loop = asyncio.get_running_loop()
        exit_data = await loop.run_in_executor(None, lambda: container.wait(timeout=timeout))
        exit_code = exit_data.get("StatusCode", -1)

        stdout = await loop.run_in_executor(None, lambda: container.logs(stdout=True, stderr=False))
        stderr = await loop.run_in_executor(None, lambda: container.logs(stdout=False, stderr=True))

        return {
            "exit_code": exit_code,
            "stdout": stdout.decode().strip() if isinstance(stdout, bytes) else "",
            "stderr": stderr.decode().strip() if isinstance(stderr, bytes) else "",
            "success": exit_code == 0,
        }
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False}
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
