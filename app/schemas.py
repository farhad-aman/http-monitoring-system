from datetime import datetime
from pydantic import BaseModel


class ServerBase(BaseModel):
    address: str


class ServerCreate(ServerBase):
    pass


class Server(ServerBase):
    id: int
    success: int
    failure: int
    last_failure: int
    created_at: datetime

    class Config:
        orm_mode = True
