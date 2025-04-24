from fastapi import FastAPI

from API import user, prediction, profile, config, assets

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Ensure POST is allowed
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(prediction.router)
app.include_router(config.router)
app.include_router(profile.router)
app.include_router(assets.router)


# app.include_router(budget.router)


@app.get("/")
def welcome():
    return "Welcome to Financial Advisor sem 4! Still Testing ! Test -1000 "
