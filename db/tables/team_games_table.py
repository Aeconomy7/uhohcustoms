
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from config import SCHEMA_NAME
from db.tables.base_db_class import BaseDbClass
from db.tables.users_table import usersTable
from db.tables.teams_table import teamsTable
from db.tables.game_data_table import gameDataTable

class teamGamesTable(BaseDbClass):
    __tablename__ = 'team_games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_uuid = Column(String, ForeignKey(f'{SCHEMA_NAME}.teams.team_uuid'), nullable=False)
    game_id = Column(String, ForeignKey(f'{SCHEMA_NAME}.game_data.game_id'), nullable=False)
    team = relationship('Team', backref='games')
    game = relationship('GameData', backref='teams')

teamsTable.games = relationship('teamGamesTable', back_populates='team')

teamGamesTable.team = relationship('teamsTable', back_populates='games')