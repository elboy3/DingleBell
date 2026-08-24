"""FastAPI entry point - pure JSON API, consumed by the React app in
frontend/.

    uvicorn webapp.app:app --reload --port 8000   # local dev
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import api_identity, api_listings

app = FastAPI(title="Apartment Hunt API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_identity.router)
app.include_router(api_listings.router)
