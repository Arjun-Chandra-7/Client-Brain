from fastapi import FastAPI
from app.api import brain, clients, research
from app.db.session import Base, engine
import app.models  # Register models before create_all.

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Client Brain", version="0.1.0", description="Persistent, source-backed client intelligence for VIRALYST.")
app.include_router(clients.router); app.include_router(brain.router); app.include_router(research.router)


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Open /research/test to test Client Brain in a browser, or /docs for the API."}


@app.get("/health")
def health(): return {"status": "ok", "service": "client-brain", "version": "0.1.0"}
