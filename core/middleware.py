# Initialize logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from fastapi import Request
from fastapi.responses import JSONResponse
import jwt
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Middleware to verify token and extract user from it
async def token_verification_middleware(request: Request, call_next):
    # Allow public routes
    open_routes = ["/","/auth", "/openapi.json", "auth/user/reg", "/auth/login"]
    if any(request.url.path.startswith(route) for route in open_routes):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        required_fields = ["sub", "user_id", "role", "username"]
        for field in required_fields:
            if field not in payload:
                return JSONResponse(status_code=401, content={"detail": f"Missing '{field}' in token"})

        # Optional: check if user is disabled using 'disabled' claim (if you set that in token)
        if payload.get("disabled", False):
            return JSONResponse(status_code=403, content={"detail": "User is disabled"})

        # Attach user data from token to request
        request.state.user = {
            "id": payload["user_id"],
            "username": payload["username"],
            "role": payload["role"]
        }

    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expired"})
    except jwt.PyJWTError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    return await call_next(request)
