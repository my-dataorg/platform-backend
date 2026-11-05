"""Proxy Business API for platform-frontend (dashboard manage businesses)."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import get_current_user
from app.config import settings
from app.services.business_upstream import business_api_upstream_base

router = APIRouter(prefix="/v1/business", tags=["business-gateway"])


async def _forward(request: Request, upstream_path: str) -> Response:
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Missing token")

    base = business_api_upstream_base()
    url = f"{base}{upstream_path}"
    headers = {"Authorization": auth}
    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type

    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            upstream = await client.request(
                request.method,
                url,
                headers=headers,
                content=body if body else None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Business API unreachable at {base} (configured {settings.business_api_url}). Is business-backend running on the Docker network?",
        ) from exc

    media_type = upstream.headers.get("content-type", "application/json")
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media_type)


@router.get("/businesses")
@router.post("/businesses")
async def businesses_collection(request: Request, _: dict = Depends(get_current_user)):
    return await _forward(request, "/v1/businesses")


@router.delete("/businesses/{business_id}")
async def delete_business(
    request: Request, business_id: str, _: dict = Depends(get_current_user)
):
    return await _forward(request, f"/v1/businesses/{business_id}")
