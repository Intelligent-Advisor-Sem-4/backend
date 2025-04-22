from fastapi import FastAPI

from API import user,prediction
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



@app.get("/")
def welcome():
    return "Welcome to Financial Advisor sem 4! Still Testing ! Test -1000 "