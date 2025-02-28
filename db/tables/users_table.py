

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.tables.base_db_class import BaseDbClass

class usersTable(BaseDbClass):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    user_uuid = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # teams = relationship('teamsTable', back_populates='team_captain')
    # user_teams = relationship('userTeamsTable', back_populates='user')

# from db.tables.base_db_class import BaseDbClass
# from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
# from sqlalchemy.orm import mapped_column
# from sqlalchemy.orm import relationship

# class usersTable(BaseDbClass):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     username = Column(String, unique=True, nullable=False)
#     email = Column(String, unique=True, nullable=False)
#     user_uuid = Column(String, unique=True, nullable=False)
#     password_hash = Column(String, nullable=False)
#     riot_id = Column(String)
#     riot_access_token = Column(String)
#     riot_refresh_token = Column(String)

# #########
# # USERS #
# #########
# def __create_users_table(self):
# 	sql_query = """ CREATE TABLE IF NOT EXISTS users (
# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
# 			username TEXT NOT NULL UNIQUE,
# 			email TEXT NOT NULL UNIQUE,
# 			user_uuid TEXT NOT NULL UNIQUE,
# 			password_hash TEXT NOT NULL,
# 			riot_id TEXT,
# 			riot_access_token,
# 			riot_refresh_token
# 		);"""
# 	try:
# 		cursor = self.__conn.cursor()
# 		cursor.execute(sql_query)
# 		self.__conn.commit()
# 		return True
# 	except Error as e:
# 		print(f"[!][CUSTOMS_DB][__create_users_table] ERROR: {e}")
# 		return False