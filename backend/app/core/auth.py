import requests
from fastapi import Header, HTTPException

from app.config import settings


class CurrentUser:
    def __init__(self, id: str, email: str | None, role: str):
        self.id = id
        self.email = email
        self.role = role


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Verifies the Supabase-issued access token by asking Supabase's own Auth
    API to resolve it -- one network round-trip per request, but it means
    this backend never has to manage JWT secrets/JWKS or keep them in sync
    with Supabase's own key rotation. Fine for this project's scale; a
    high-traffic service would cache/verify locally instead.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()

    response = requests.get(
        f"{settings.supabase_url}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
        timeout=10,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    data = response.json()
    role = (data.get("user_metadata") or {}).get("role", "job_seeker")
    return CurrentUser(id=data["id"], email=data.get("email"), role=role)
