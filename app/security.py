import hashlib
import hmac

from fastapi import Header, HTTPException, Request, status

from app.config import get_settings


async def require_api_token(
    authorization: str | None = Header(default=None),
) -> None:
    expected = f"Bearer {get_settings().api_token}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid bearer token",
        )


async def verify_webhook(request: Request) -> bytes:
    signature = request.headers.get("x-gtm-signature", "")
    body = await request.body()
    expected = hmac.new(
        get_settings().webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid webhook signature",
        )
    return body

