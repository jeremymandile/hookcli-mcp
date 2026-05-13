import asyncio
import httpx
import os
from typing import Dict, Any

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")


async def request_approval(
    hook_id: str,
    event_id: str,
    payload: Dict[str, Any],
    command: str,
    slack_channel: str = "#ops-alerts",
) -> bool:
    if not SLACK_BOT_TOKEN:
        return False

    text = f"⚠️ *Approval required for hook execution*\nHook: `{hook_id}`\nEvent: `{event_id}`\nCommand: `{command[:200]}`"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {
            "type": "actions",
            "block_id": f"approval_{hook_id}_{event_id}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "value": f"approve_{hook_id}_{event_id}",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny"},
                    "style": "danger",
                    "value": f"deny_{hook_id}_{event_id}",
                },
            ],
        },
    ]

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": slack_channel, "text": text, "blocks": blocks},
        )

    return True
