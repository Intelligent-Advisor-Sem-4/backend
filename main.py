from fastapi import FastAPI
from API import user, prediction, profile, config, assets, risk_analyser
from fastapi.middleware.cors import CORSMiddleware
from core.middleware import token_verification_middleware
import os

app = FastAPI()

# Get the frontend URL from environment variable or use a default for development
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Define all allowed origins
allowed_origins = [
    FRONTEND_URL,
    "https://production.d3femg7tg1inty.amplifyapp.com"
    # Add any additional frontend domains that need access
    # "https://your-production-app.com",
    # "https://staging-app.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specific origins instead of wildcard
    allow_credentials=True,  # Allow cookies to be sent
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Specify the methods explicitly
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    expose_headers=["Content-Length"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

app.middleware("http")(token_verification_middleware)

app.include_router(user.router)
app.include_router(prediction.router)
app.include_router(config.router)
app.include_router(profile.router)
app.include_router(assets.router)
app.include_router(risk_analyser.router)


@app.get("/")
def welcome():
    return "Welcome to Financial Advisor sem 4! Still Testing ! Test -1000 "
