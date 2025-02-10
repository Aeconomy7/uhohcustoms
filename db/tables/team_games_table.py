from db.tables.base_db_class import BaseDbClass
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class teamGamesTable(BaseDbClass):
    __tablename__ = 'team_games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_uuid = Column(String, ForeignKey('teams.team_uuid'), nullable=False)
    game_id = Column(String, ForeignKey('game_data.game_id'), nullable=False)
    team = relationship('Team', backref='games')
    game = relationship('GameData', backref='teams')