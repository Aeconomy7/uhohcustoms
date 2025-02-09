from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class currentPatchTable(BaseDbClass):
    __tablename__ = 'current_patch'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patch_version = Column(String, nullable=False)

