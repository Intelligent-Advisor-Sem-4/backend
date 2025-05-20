from fastapi import APIRouter, Request
from typing import Dict

router = APIRouter(
    prefix="/auth-test",
    tags=["Authentication Testing"],
    responses={404: {"description": "Not found"}},
)


@router.get("/verify")
async def auth_verification_endpoint(request: Request) -> Dict:
    """
    A simple endpoint that requires authentication to access.
    Used for testing authentication middleware.

    Returns:
        Dict: Welcome message with authenticated user info
    """
    # The user data will be available in request.state.user if auth middleware worked
    print("*************************************")
    print(request.state.user)
    print("*************************************")
    user_data = request.state.user

    return {
        "status": "success",
        "message": "Authentication successful!",
        "user": {
            "id": user_data.get("id"),
            "username": user_data.get("username", "Unknown"),
            "role": user_data.get("role")
        }
    }


@router.get("/admin-verify")
async def admin_verification_endpoint(request: Request) -> Dict:
    """
    A simple endpoint that requires admin authentication to access.
    Used for testing admin middleware.

    Returns:
        Dict: Welcome message for admin users
    """
    user_data = request.state.user

    if user_data.get("role") != "ADMIN":
        return {
            "status": "error",
            "message": "This endpoint requires admin privileges"
        }

    return {
        "status": "success",
        "message": "Admin authentication successful!",
        "user": {
            "id": user_data.get("id"),
            "username": user_data.get("username", "Unknown"),
            "role": user_data.get("role")
        }
    }
