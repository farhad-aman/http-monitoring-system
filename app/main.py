import os
import time
import logging
import httpx

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from crud import get_server, get_servers, create_server, update_server_status
from database import SessionLocal, engine
from models import Base
from schemas import ServerCreate, Server

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def is_server_healthy(address: str) -> bool:
    if not address.startswith(("http://", "https://")):
        address = "http://" + address
    try:
        response = httpx.get(address, follow_redirects=True)
        if response.status_code == 200:
            logger.info(f"Server at {address} is healthy.")
            return True
        else:
            logger.warning(f"Server at {address} returned status code {response.status_code}.")
            return False
    except httpx.RequestError as e:
        logger.error(f"Error while checking server at {address}: {e}")
        return False


def monitor():
    logger.info("Monitoring Started!")
    db: Session = SessionLocal()
    try:
        servers = get_servers(db)
        for server in servers:
            is_healthy = is_server_healthy(server.address)
            last_failure = int(time.time()) if not is_healthy else server.last_failure
            update_server_status(db, server.id, is_healthy, last_failure)
            logger.info(f"Updated status for server {server.address}: Healthy - {is_healthy}")
    except Exception as e:
        logger.exception("An error occurred during the monitoring process: ", e)
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(monitor, 'interval', minutes=int(os.getenv("MONITOR_INTERVAL", 1)))
scheduler.start()

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/server/", response_model=Server)
def create_server_api(server: ServerCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating a new server entry: {server}")
    try:
        return create_server(db=db, server=server)
    except Exception as e:
        logger.error(f"Error creating server {server}: {e}")
        raise HTTPException(status_code=500, detail="Error creating server")


@app.get("/api/server/all", response_model=list[Server])
def read_servers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info(f"Fetching list of servers: skip {skip}, limit {limit}")
    servers = get_servers(db, skip=skip, limit=limit)
    return servers


@app.get("/api/server/{server_id}", response_model=Server)
def read_server(server_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching server with ID: {server_id}")
    db_server = get_server(db, server_id=server_id)
    if db_server is None:
        logger.warning(f"Server not found: {server_id}")
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server
