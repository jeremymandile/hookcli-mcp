import hmac
import hashlib
import time
import json
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(prefix="/approvals", tags=["approvals"])

SLACK_SIGNING_SECRET = "your-slack-signing-secret"
pending_approvals: Dict[str, Any] = {}


def verify_slack_signature(payload: str, timestamp: str, signature: str) -> bool:
    sig_basestring = f"v0:{timestamp}:{payload}"
    my_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(my_sig, signature)


class ApprovalRequest(BaseModel):
    hook_id: str
    action_description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = Field(default=300, ge=30, le=3600)


class ApprovalResponse(BaseModel):
    approval_id: str
    callback_url: str
    expires_in: int


@router.post("/request", response_model=ApprovalResponse)
async def request_approval(req: ApprovalRequest):
    approval_id = f"appr_{req.hook_id}_{int(time.time())}"
    return ApprovalResponse(
        approval_id=approval_id,
        callback_url="/api/approvals/callback",
        expires_in=req.timeout_sec,
    )


@router.post("/callback")
async def approval_callback(request: Request):
    form = await request.form()
    payload_str = form.get("payload", "{}")
    timestamp = form.get("timestamp", "0")
    signature = form.get("X-Slack-Signature", "")

    if not verify_slack_signature(payload_str, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(payload_str)
    action = payload.get("actions", [{}])[0]
    approval_id = action.get("value", "unknown")
    approved = action.get("name") == "approve"

    key = approval_id
    if key in pending_approvals:
        pending_approvals[key]["result"] = approved
        pending_approvals[key]["event"].set()

    return {"status": "ack", "decision": "approved" if approved else "rejected"}


@router.get("/status/{approval_id}")
async def get_approval_status(approval_id: str):
    state = pending_approvals.get(approval_id)
    if not state:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": approval_id, "status": state.get("status", "unknown")}
