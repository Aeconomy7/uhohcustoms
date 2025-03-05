from sqlalchemy.orm import DeclarativeBase
from config import SCHEMA_NAME

class BaseDbClass(DeclarativeBase):
    __table_args__ = {"schema": SCHEMA_NAME} if SCHEMA_NAME else {}
    
    pass