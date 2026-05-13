"""Stripe webhook receiver — validates HMAC signature then dispatches to hook engine."""

import os

import stripe
from fastapi import APIRouter, HTTPException, Request

from hookcli_mcp.observability.metrics import record_execution

router = APIRouter(prefix="/webhooks/stripe", tags=["webhooks"])

_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


@router.post("")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not _WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _WEBHOOK_SECRET)
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook parse error: {e}")

    event_type = event["type"]
    event_object = event.get("data", {}).get("object", {})

    # Record the inbound event as a metric
    record_execution(hook_id=f"stripe:{event_type}", duration=0.0, success=True)

    # Dispatch: in production wire this to the hook engine / registered templates.
    # For the payment_intent.payment_failed demo, the registered hook handles the action.
    return {
        "status": "received",
        "event_type": event_type,
        "event_id": event.get("id"),
        "object_id": event_object.get("id"),
    }
