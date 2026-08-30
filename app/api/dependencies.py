from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Client


def client_or_404(client_id: str, db: Session = Depends(get_db)) -> Client:
    client = db.get(Client, client_id)
    if not client: raise HTTPException(404, "Client not found")
    return client
