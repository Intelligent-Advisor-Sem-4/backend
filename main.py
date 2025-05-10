from fastapi import FastAPI

from API import (
    user,
    prediction,
    profile,
    config,
    assets,
    risk_analyser,
    budget,
    explain_portfolio,
)

from fastapi.middleware.cors import CORSMiddleware
from core.middleware import token_verification_middleware, admin_access_middleware
import os

app = FastAPI()

# # Define allowed origins with environment variable support
# allowed_origins = [
#     "https://intellifinance.shancloudservice.com",
#     "https://intellifinance2.shancloudservice.com",
#     "http://localhost:3000",
# ]

# # # Add frontend URL from environment variable if exists
# frontend_url = os.getenv("FRONTEND_URL")
# if frontend_url:
#     # Split by comma if multiple URLs are provided
#     additional_origins = [url.strip() for url in frontend_url.split(",")]
#     allowed_origins.extend(additional_origins)

# # Regex pattern for all shancloudservice.com subdomains
# allowed_origin_regex = r"https://.*\.shancloudservice\.com"

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=allowed_origins,
#     allow_origin_regex=allowed_origin_regex,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
#     allow_headers=["*"],
#     expose_headers=["Content-Length"],
#     max_age=600,
# )


# # # Uncomment when ready to enforce token verification
# app.middleware("http")(admin_access_middleware)
# app.middleware("http")(token_verification_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(prediction.router)
app.include_router(config.router)
app.include_router(profile.router)
app.include_router(assets.router)
app.include_router(budget.router)
app.include_router(risk_analyser.router)
app.include_router(explain_portfolio.router)


@app.get("/")
def welcome():
    return "Welcome to Financial Advisor sem 4! Still Testing ! Test -1000 "
