from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.tables.base_db_class import BaseDbClass

class teamsTable(BaseDbClass):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_name = Column(String, nullable=False)
    team_uuid = Column(String, unique=True, nullable=False)
    team_captain_uuid = Column(Integer, ForeignKey('users.id'), nullable=False)

    # team_captain = relationship('usersTable', back_populates='teams')
    # members = relationship('userTeamsTable', back_populates='team')

	# def __create_teams_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS teams (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			team_name TEXT NOT NULL,
	# 			team_uuid TEXT NOT NULL UNIQUE,
	# 			team_captain_uuid INTEGER NOT NULL,
	# 			FOREIGN KEY(team_captain_uuid) REFERENCES users(id)
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_users_table] ERROR:  {e}")
	# 		return False