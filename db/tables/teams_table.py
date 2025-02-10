from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class teamsTable(BaseDbClass):
    __tablename__ = 'teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_name = Column(String, nullable=False)
    team_uuid = Column(String, unique=True, nullable=False)
    team_captain_uuid = Column(String, ForeignKey('users.user_uuid'), nullable=False)
    captain = relationship('User', backref='captain_of_teams')