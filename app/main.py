import os
import time
import logging
import httpx

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

from crud import get_server, get_servers, create_server, update_server_status
from database import MasterSessionLocal, ReplicaSessionLocal, master_engine
import models
import schemas

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Prometheus metrics
DB_REQUEST_COUNT = Counter(
    "db_request_count",
    "Total number of database requests made.",
    ["status"]
)
DB_REQUEST_LATENCY = Histogram(
    "db_request_latency_seconds",
    "Latency of database requests (in seconds)."
)


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
    db: Session = MasterSessionLocal()
    try:
        start_time = time.time()
        servers = get_servers(db)
        DB_REQUEST_LATENCY.observe(time.time() - start_time)
        DB_REQUEST_COUNT.labels(status="success").inc()
        for server in servers:
            is_healthy = is_server_healthy(server.address)
            last_failure = int(time.time()) if not is_healthy else server.last_failure
            update_server_status(db, server.id, is_healthy, last_failure)
            logger.info(f"Updated status for server {server.address}: Healthy - {is_healthy}")
    except Exception as e:
        logger.exception("An error occurred during the monitoring process: ", e)
        DB_REQUEST_COUNT.labels(status="failure").inc()
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(monitor, 'interval', minutes=int(os.getenv("MONITOR_INTERVAL", 1)))
scheduler.start()

models.Base.metadata.create_all(bind=master_engine)

app = FastAPI()
Instrumentator().instrument(app).expose(app)


def db_factory(operation='read'):
    def get_db():
        if operation == 'read':
            db = ReplicaSessionLocal()
            try:
                yield db
            finally:
                db.close()
        else:
            db = MasterSessionLocal()
            try:
                yield db
            finally:
                db.close()

    return get_db


@app.post("/api/server/", response_model=schemas.Server)
def create_server_api(server: schemas.ServerCreate, db: Session = Depends(db_factory(operation='write'))):
    logger.info(f"Creating a new server entry: {server}")
    try:
        start_time = time.time()
        server = create_server(db=db, server=server)
        DB_REQUEST_LATENCY.observe(time.time() - start_time)
        DB_REQUEST_COUNT.labels(status="success").inc()
        return server
    except Exception as e:
        logger.error(f"Error creating server {server}: {e}")
        DB_REQUEST_COUNT.labels(status="failure").inc()
        raise HTTPException(status_code=500, detail="Error creating server")


@app.get("/api/server/all", response_model=list[schemas.Server])
def read_servers(skip: int = 0, limit: int = 100, db: Session = Depends(db_factory(operation='read'))):
    logger.info(f"Fetching list of servers: skip {skip}, limit {limit}")
    start_time = time.time()
    servers = get_servers(db, skip=skip, limit=limit)
    DB_REQUEST_LATENCY.observe(time.time() - start_time)
    if servers is None:
        DB_REQUEST_COUNT.labels(status="failure").inc()
        logger.warning("No servers found.")
        raise HTTPException(status_code=404, detail="No servers found.")
    DB_REQUEST_COUNT.labels(status="success").inc()
    return servers


@app.get("/api/server/{server_id}", response_model=schemas.Server)
def read_server(server_id: int, db: Session = Depends(db_factory(operation='read'))):
    logger.info(f"Fetching server with ID: {server_id}")
    start_time = time.time()
    db_server = get_server(db, server_id=server_id)
    DB_REQUEST_LATENCY.observe(time.time() - start_time)
    if db_server is None:
        DB_REQUEST_COUNT.labels(status="failure").inc()
        logger.warning(f"Server not found: {server_id}")
        raise HTTPException(status_code=404, detail="Server not found")
    DB_REQUEST_COUNT.labels(status="success").inc()
    return db_server


@app.get("/health/liveness")
def liveness_probe():
    return {"status": "alive"}


@app.get("/health/readiness")
def readiness_probe():
    try:
        with MasterSessionLocal() as db:
            db.query(models.Server).first()
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return {"status": "not ready"}, 503


@app.get("/hello")
def hello():
    return {"message": "hello"}
