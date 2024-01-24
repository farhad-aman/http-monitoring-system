from sqlalchemy.orm import Session

from models import Server
from schemas import ServerCreate


def get_server(db: Session, server_id: int):
    return db.query(Server).filter(Server.id == server_id).first()


def get_servers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Server).offset(skip).limit(limit).all()


def create_server(db: Session, server: ServerCreate):
    db_server = Server(address=server.address)
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server


def update_server_status(db: Session, server_id: int, is_healthy: bool, last_failure: int):
    server = db.query(Server).filter(Server.id == server_id).first()
    if server:
        if is_healthy:
            server.success += 1
        else:
            server.failure += 1
            server.last_failure = last_failure
        db.commit()
    else:
        print("Server Not Found!")
