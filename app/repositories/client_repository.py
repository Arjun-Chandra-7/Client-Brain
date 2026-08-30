from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Client


class ClientRepository:
    def __init__(self, db: Session): self.db = db
    def create(self, client: Client) -> Client:
        self.db.add(client); self.db.commit(); self.db.refresh(client); return client
    def get(self, client_id: str) -> Client | None: return self.db.get(Client, client_id)
    def list(self) -> list[Client]: return list(self.db.scalars(select(Client).order_by(Client.created_at.desc())))
