from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.tables.base_db_class import BaseDbClass
from db.tables.users_table import usersTable
from db.tables.teams_table import teamsTable

class userTeamsTable(BaseDbClass):
    __tablename__ = 'user_teams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_uuid = Column(String, ForeignKey('users.user_uuid'), nullable=False)
    team_uuid = Column(String, ForeignKey('teams.team_uuid'), nullable=False)
    role = Column(String, default='Pending', nullable=False)

    # user = relationship('usersTable', back_populates='user_teams')
    # team = relationship('teamsTable', back_populates='members')

# Define relationships after both classes have been defined
usersTable.user_teams = relationship('userTeamsTable', back_populates='user')
teamsTable.members = relationship('userTeamsTable', back_populates='team')

userTeamsTable.user = relationship('usersTable', back_populates='user_teams')
userTeamsTable.team = relationship('teamsTable', back_populates='members')

# def __create_user_teams_table(self):
# 	sql_query = """ CREATE TABLE IF NOT EXISTS user_teams (
# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
# 			user_uuid TEXT NOT NULL,
# 			team_uuid TEXT NOT NULL,
# 			role TEXT NOT NULL DEFAULT 'Pending',
# 			FOREIGN KEY(user_uuid) REFERENCES users(user_uuid),
# 			FOREIGN KEY(team_uuid) REFERENCES teams(team_uuid)
# 		);"""
# 	try:
# 		cursor = self.__conn.cursor()
# 		cursor.execute(sql_query)
# 		self.__conn.commit()
# 		return True
# 	except Error as e:
# 		print(f"[!][CUSTOMS_DB][__create_user_teams_table] ERROR: {e}")
# 		return False