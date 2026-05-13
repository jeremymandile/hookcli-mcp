from fastapi import APIRouter, Response
from prometheus_client import REGISTRY, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def get_metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
