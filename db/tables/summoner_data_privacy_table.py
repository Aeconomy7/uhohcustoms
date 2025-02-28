from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class summonerDataPrivacyTable(BaseDbClass):
    __tablename__ = "summoner_data_privacy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    riot_id = Column(String, nullable=False)
    team_uuid = Column(String, nullable=False)