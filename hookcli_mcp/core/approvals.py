import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


class ApprovalState:
    def __init__(self):
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._events: Dict[str, asyncio.Event] = {}

    async def create(self, approval_id: str, hook_id: str, context: Dict[str, Any], timeout_sec: int = 300) -> None:
        self._pending[approval_id] = {
            "status": ApprovalStatus.PENDING,
            "hook_id": hook_id,
            "context": context,
            "created_at": time.time(),
            "decision": None,
        }
        self._events[approval_id] = asyncio.Event()

    async def resolve(self, approval_id: str, approved: bool) -> Optional[Dict[str, Any]]:
        if approval_id not in self._pending:
            return None
        state = self._pending[approval_id]
        state["status"] = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        state["decision"] = approved
        state["resolved_at"] = time.time()
        self._events[approval_id].set()
        return state

    async def wait_for_decision(self, approval_id: str, timeout_sec: int = 300) -> Dict[str, Any]:
        if approval_id not in self._events:
            raise KeyError(f"Approval {approval_id} not found")
        try:
            await asyncio.wait_for(self._events[approval_id].wait(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            state = self._pending.get(approval_id)
            if state:
                state["status"] = ApprovalStatus.TIMED_OUT
        return self._pending.get(approval_id, {})


approval_store = ApprovalState()
