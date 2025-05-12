# Initialize logging
import logging
import json
import urllib.parse

from models.models import AccessLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import jwt
import os
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY") 
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")
ALGORITHM = "HS256"


# Middleware to verify token from either cookies or Authorization header
async def token_verification_middleware(request: Request, call_next):
   
    origin = request.headers.get("Origin")
    logger.info(f"Request received from origin: {origin or 'Unknown'}")

    # Allow public routes
    open_routes = ["/auth", "/openapi.json", "/auth/user/reg", "/auth/login", "/docs", "/triggers"]
    if request.url.path == "/" or request.url.path == "/budget/email" or any(
            request.url.path.startswith(route) for route in open_routes):
        return await call_next(request)

    token = None
    auth_source = None

    # Check for token in cookies
    token_cookie = request.cookies.get("token")
    # Log all values in the cookie
  
    print(f"Cookies received: {token_cookie}")
    if token_cookie:
        token = token_cookie
        auth_source = "cookie"
        logger.debug("Using token from cookie")

    # If not found in cookies, check Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            auth_source = "header"
            logger.debug("Using token from Authorization header")

    # If no token found in either location
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication token not found in cookies or Authorization header"}
        )

    try:
        # Decode and verify token
        print("1 pass")
        print(type(token),type(SECRET_KEY))
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        required_fields = ["sub", "user_id", "role"]
        for field in required_fields:
            if field not in payload:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"Missing '{field}' in token"}
                )

        # Check if user is disabled
        if payload.get("disabled", False):
            return JSONResponse(
                status_code=403,
                content={"detail": "User is disabled"}
            )

        # Initialize user data from token
        user_data = {
            "id": payload["user_id"],
            "role": payload["role"]
        }

        # Add username if available in token
        if "username" in payload:
            user_data["username"] = payload["username"]

        # For cookie-based auth, try to get additional user data from user cookie
        if auth_source == "cookie":
            user_cookie = request.cookies.get("user")
            if user_cookie:
                try:
                    decoded_cookie = urllib.parse.unquote(user_cookie)
                    cookie_data = json.loads(decoded_cookie)
                    # Update user_data with values from cookie
                    user_data.update(cookie_data)
                    logger.debug("Enhanced user data from user cookie")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse user cookie as JSON")

        # Attach final user data to request
        request.state.user = user_data
        logger.info(
            f"User authenticated via {auth_source}: {user_data.get('username', user_data['id'])}"
        )

    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Token expired"}
        )
    except jwt.PyJWTError as e:
        logger.error(f"JWT error: {str(e)}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid token"}
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Authentication error"}
        )

    return await call_next(request)


# Middleware to verify admin access for specific routes
async def admin_access_middleware(request: Request, call_next):
    # Define admin-only routes
    admin_only_routes = [
        {"path": "/assets/create-stock", "method": "POST"},
        {"path": "/assets/{stock_id}/status", "method": "PUT"},
        {"path": "/assets/{stock_id}", "method": "DELETE"},
        {"path": "/risk-analysis/{ticker}/regenerate-news-analysis", "method": "GET"}
    ]

    # Check if the current route requires admin access
    current_path = request.url.path
    current_method = request.method

    requires_admin = False
    for route in admin_only_routes:
        # Handle path parameters by comparing path segments
        route_parts = route["path"].split("/")
        current_parts = current_path.split("/")

        if len(route_parts) == len(current_parts) and route["method"] == current_method:
            matches = True
            for i, part in enumerate(route_parts):
                if part.startswith("{") and part.endswith("}"):
                    # This is a path parameter, skip exact matching
                    continue
                if part != current_parts[i]:
                    matches = False
                    break

            if matches:
                requires_admin = True
                break

    # If route requires admin access, check user role
    if requires_admin:
        # Ensure user is authenticated
        if not hasattr(request.state, "user"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

        user_data = request.state.user
        if user_data.get("role") != AccessLevel.ADMIN.value:
            return JSONResponse(
                status_code=403,
                content={"detail": "Admin access required for this operation"}
            )

    # Continue with the request
    return await call_next(request)
