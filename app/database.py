import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_MASTER_URL = os.getenv("DATABASE_MASTER_URL", "postgresql://user:password@localhost/dbname")
SQLALCHEMY_DATABASE_REPLICA_URL = os.getenv("DATABASE_REPLICA_URL", "postgresql://user:password@localhost/dbname")

master_engine = create_engine(SQLALCHEMY_DATABASE_MASTER_URL)
replica_engine = create_engine(SQLALCHEMY_DATABASE_REPLICA_URL)

MasterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=master_engine)
ReplicaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=replica_engine)

Base = declarative_base()
