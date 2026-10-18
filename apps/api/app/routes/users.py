"""Current-user endpoint (credit balance for the nav)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .. import credits
from ..auth import get_current_user
from ..schemas import MeResponse

router = APIRouter()


@router.get("/users/me", response_model=MeResponse)
def get_me(user: Annotated[dict, Depends(get_current_user)]) -> JSONResponse:
    """Return the signed-in user's id, email, and credit balance.

    ``credits`` is None when Supabase is not configured (local-dev mode —
    renders are free there). 401 when anonymous.
    """
    balance = credits.get_balance(user_id=user["id"])
    return JSONResponse(
        {
            "id": user["id"],
            "email": user.get("email"),
            "credits": balance,
        }
    )
