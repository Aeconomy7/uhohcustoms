from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
class usersTable(BaseDbClass):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    user_uuid = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    riot_id = Column(String)
    riot_access_token = Column(String)
    riot_refresh_token = Column(String)