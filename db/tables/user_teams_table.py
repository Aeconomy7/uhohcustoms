from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
class userTeamsTable(BaseDbClass):
    __tablename__ = 'user_teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_uuid = Column(String, ForeignKey('users.user_uuid'), nullable=False)
    team_uuid = Column(String, ForeignKey('teams.team_uuid'), nullable=False)
    role = Column(String, default='Pending')
    user = relationship('User', backref='teams')
    team = relationship('Team', backref='members')