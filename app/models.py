from sqlalchemy import Column, Integer, String, BigInteger, func, DateTime
from database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    success = Column(Integer, default=0)
    failure = Column(Integer, default=0)
    last_failure = Column(BigInteger, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
