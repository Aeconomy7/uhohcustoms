from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class gameDataTable(BaseDbClass):
    __tablename__ = 'game_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, unique=True, nullable=False)
    game_data_blob = Column(LargeBinary, nullable=False)