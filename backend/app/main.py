"""FastAPI application entry point.

Mounts all routers and configures CORS for the local Vue dev server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import category, clarify, search, sessions

app = FastAPI(title="the-short-list", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "the-short-list backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(sessions.router)
app.include_router(clarify.router)
app.include_router(search.router)
app.include_router(category.router)
