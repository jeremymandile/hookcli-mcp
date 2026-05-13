from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def get_metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
