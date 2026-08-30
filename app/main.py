from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api import brain, clients, research
from app.db.session import Base, engine
import app.models  # Register models before create_all.

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Client Brain", version="0.1.0", description="Persistent, source-backed client intelligence for VIRALYST.")
app.include_router(clients.router); app.include_router(brain.router); app.include_router(research.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return research.test_page()


@app.get("/health")
def health(): return {"status": "ok", "service": "client-brain", "version": "0.1.0"}
