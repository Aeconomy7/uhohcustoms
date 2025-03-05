import datetime
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, func, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sqlite3
from sqlite3 import Error

from db.tables.base_db_class import BaseDbClass

from config import DB_TYPE, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, SQLALCHEMY_DATABASE_URI, SCHEMA_NAME
from db.tables.base_db_class import BaseDbClass
from db.tables.users_table import usersTable
from db.tables.teams_table import teamsTable
from db.tables.user_teams_table import userTeamsTable
from db.tables.game_data_table import gameDataTable
from db.tables.team_games_table import teamGamesTable
from db.tables.current_patch_table import currentPatchTable
from db.tables.summoner_data_privacy_table import summonerDataPrivacyTable

class CustomsDbHandler:
	def __init__(self):
		# DEBUG MODE
		self.__DEBUG = True
		print(f"[?][CUSTOMS_DB][__init__] DB DEBUG MODE: {self.__DEBUG}")

		if DB_TYPE == 'postgresql':
			# Create customs database if it does not exist
			try:
				conn = psycopg2.connect(f"dbname=postgres user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}")
				conn.autocommit = True
				cur = conn.cursor()
				cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
				if not cur.fetchone():
					cur.execute(f"CREATE DATABASE {DB_NAME}")
					if self.__DEBUG:
						print(f"[+][CUSTOMS_DB][__init__] Successfully created database {DB_NAME}!")
				else:
					if self.__DEBUG:
						print(f"[-][CUSTOMS_DB][__init__] Database {DB_NAME} already exists!")
				cur.close()
				conn.close()
			except Exception as e:
				print(f"[!][CUSTOMS_DB][__init__] Error creating database: {e}")

			# Reconnect to the newly created database
			try:
				conn = psycopg2.connect(f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}")
				conn.autocommit = True
				cur = conn.cursor()
				cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
				cur.close()
				conn.close()
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][__init__] Successfully created schema {SCHEMA_NAME}")
			except Exception as e:
				print(f"[!][CUSTOMS_DB][__init__] Error creating schema: {e}")

		if DB_TYPE == 'sqlite3':
			# Create customs database if it does not exist
			try:
				conn = sqlite3.connect(SQLALCHEMY_DATABASE_URI)
				cur = conn.cursor()
				cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
				if not cur.fetchone():
					if self.__DEBUG:
						print(f"[+][CUSTOMS_DB][__init__] Successfully created database {SQLALCHEMY_DATABASE_URI}!")
				else:
					if self.__DEBUG:
						print(f"[-][CUSTOMS_DB][__init__] Database {SQLALCHEMY_DATABASE_URI} already exists!")
				cur.close()
				conn.close()
			except Exception as e:
				print(f"[!][CUSTOMS_DB][__init__] Error creating database: {e}")

		self.__engine = create_engine(SQLALCHEMY_DATABASE_URI, echo=False)
		BaseDbClass.metadata.create_all(self.__engine)
		Session = sessionmaker(bind=self.__engine)
		self.__session = Session()

		print("[+][CUSTOMS_DB][__init__] Successfully initiated Customs database tables!")

	def __enter__(self):
		#Establish connection with Customs DB
		#self.__conn = self.__create_connection(self.__db_location)
		print("[+][CUSTOMS_DB][__enter__] Connected to Customs DB")

	def __exit__(self):
		self.__session.commit()
		self.__session.close()

		# # Commit changes to DB
		# self.__conn.commit()
		# # Close DB
		# self.__conn.close()
		print(f"[+][CUSTOMS_DB][__exit__] Closed connection to Customs DB")

	def get_session(self):
		return self.__session()

	# def __create_connection(self,db_file):
	# 	conn = None

	# 	# postgres connection
	# 	if DB_TYPE == 'postgresql':
	# 		try:
	# 			conn = psycopg2.connect(
	# 				host=DB_HOST,
	# 				port=DB_PORT,
	# 				dbname=DB_NAME,
	# 				user=DB_USER,
	# 				password=DB_PASSWORD
	# 			)
	# 			return conn
	# 		except psycopg2.Error as e:
	# 			print(f"Error connecting to PostgreSQL database: {e}")
	# 			return None

	# 	if DB_TYPE == 'sqlite3':
	# 	# sqlite3 connection
	# 		try:
	# 			conn = sqlite3.connect(db_file)
	# 		except Error as e:
	# 			print(e)

	# 	return conn

	#########
	# TEAMS #
	#########
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


	def get_total_users(self):
		with self.Session() as session:
			return session.query(func.count(usersTable.id)).scalar()

	def get_team_by_team_uuid(self, team_uuid):
		with self.Session() as session:
			return session.query(teamsTable).filter_by(team_uuid=team_uuid).first()

	def get_team_members(self, team_uuid):
		with self.Session() as session:
			query = (
				session.query(usersTable.username, usersTable.email, usersTable.user_uuid, 
							  func.case([(usersTable.user_uuid == teamsTable.team_captain_uuid, 'Captain')], else_='Member'))
				.join(userTeamsTable, usersTable.user_uuid == userTeamsTable.user_uuid)
				.join(teamsTable, userTeamsTable.team_uuid == teamsTable.team_uuid)
				.filter(teamsTable.team_uuid == team_uuid)
			)
			return query.all()

	def get_teams_for_user(self, user_uuid):
		with self.Session() as session:
			return (
				session.query(teamsTable.team_uuid, teamsTable.team_name)
				.join(userTeamsTable, teamsTable.team_uuid == userTeamsTable.team_uuid)
				.filter(userTeamsTable.user_uuid == user_uuid)
				.all()
			)

	def check_if_team_exists_by_team_name(self, team_name):
		with self.Session() as session:
			return session.query(teamsTable).filter_by(team_name=team_name).first()

	def check_if_team_exists_by_team_uuid(self, team_uuid):
		with self.Session() as session:
			return session.query(teamsTable).filter_by(team_uuid=team_uuid).first()

	def is_user_captain(self, user_uuid):
		with self.Session() as session:
			return session.query(teamsTable).filter_by(team_captain_uuid=user_uuid).first() is not None

	def is_user_captain_of_team(self, user_uuid, team_uuid):
		with self.Session() as session:
			return session.query(teamsTable).filter_by(team_captain_uuid=user_uuid, team_uuid=team_uuid).first() is not None

	def register_team(self, team_name, team_uuid, team_captain_uuid):
		with self.Session() as session:
			try:
				new_team = teamsTable(team_name=team_name, team_uuid=team_uuid, team_captain_uuid=team_captain_uuid)
				session.add(new_team)
				session.commit()
				return True
			except Exception as e:
				session.rollback()
				print(f"Error registering team: {e}")
				return False



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


	def get_total_teams(self):
		try:
			count = self.__session.query(func.count(teamsTable.id)).scalar()
			return count
		except Exception as e:
			print(f"[!][CUSTOMS_DB][get_total_teams] ERROR: {e}")
			return None

	def get_user_by_id(self, id):
		return self.__session.query(usersTable).filter_by(id=id).first()

	def get_user_by_user_uuid(self, user_uuid):
		return self.__session.query(usersTable).filter_by(user_uuid=user_uuid).first()

	def get_user_by_username(self, username):
		return self.__session.query(usersTable).filter_by(username=username).first()

	def get_user_by_email(self, email):
		return self.__session.query(usersTable).filter_by(email=email).first()

	def get_users_by_team_uuid(self, team_uuid):
		return self.__session.query(usersTable).join(userTeamsTable).filter(userTeamsTable.team_uuid == team_uuid).all()

	def check_if_user_email_exists(self, username, email):
		return self.__session.query(usersTable).filter((usersTable.username == username) | (usersTable.email == email)).first()

	def join_user_to_team(self, user_uuid, team_uuid, role='Pending'):
		try:
			user_team = userTeamsTable(user_uuid=user_uuid, team_uuid=team_uuid, role=role)
			self.__session.add(user_team)
			self.__session.commit()
			return True
		except Exception as e:
			print(f"[!][CUSTOMS_DB][join_user_to_team] ERROR: {e}")
			return False

	def remove_user_from_team(self, user_uuid, team_uuid):
		try:
			self.__session.query(userTeamsTable).filter_by(user_uuid=user_uuid, team_uuid=team_uuid).delete()
			self.__session.commit()
			return True
		except Exception as e:
			print(f"[!][CUSTOMS_DB][remove_user_from_team] ERROR: {e}")
			return False

	def register_user(self, username, user_uuid, email, password_hash):
		try:
			user = usersTable(username=username, user_uuid=user_uuid, email=email, password_hash=password_hash)
			self.__session.add(user)
			self.__session.commit()
			return True
		except Exception as e:
			print(f"[!][CUSTOMS_DB][register_user] ERROR: {e}")
			return False

	def get_user_team_role(self, user_uuid, team_uuid):
		user_team = self.__session.query(userTeamsTable).filter_by(user_uuid=user_uuid, team_uuid=team_uuid).first()
		return user_team.role if user_team else None

	def approve_user_to_team(self, user_uuid, team_uuid):
		try:
			self.__session.query(userTeamsTable).filter_by(user_uuid=user_uuid, team_uuid=team_uuid).update({"role": "Member"})
			self.__session.commit()
			return True
		except Exception as e:
			print(f"[!][CUSTOMS_DB][approve_user_to_team] ERROR: {e}")
			return False

	def reject_user_from_team(self, user_uuid, team_uuid):
		return self.remove_user_from_team(user_uuid, team_uuid)

	def get_all_team_members(self, team_uuid):
		return self.__session.query(usersTable.username, userTeamsTable.role, usersTable.user_uuid).join(userTeamsTable).filter(userTeamsTable.team_uuid == team_uuid).all()

	def get_team_members_pending(self, team_uuid):
		return self.__session.query(usersTable.user_uuid, usersTable.username).join(userTeamsTable).filter(userTeamsTable.team_uuid == team_uuid, userTeamsTable.role == 'Pending').all()


	# ###########
	# # CONTENT #
	# ###########
	# # def __create_content_table(self):
	# # 	sql_query = """ CREATE TABLE IF NOT EXISTS content (
	# # 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# # 			content_id TEXT NOT NULL,
	# # 			content_category TEXT NOT NULL,
	# # 			last_updated_patch TEXT NOT NULL,
	# # 			content_path TEXT NOT NULL
	# # 		);"""
	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query)
	# # 		self.__conn.commit()
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][__create_content_table] ERROR: {e}")
	# # 		return False


	# ##########
	# # PLAYER #
	# ##########
	# # def __create_players_table(self):
	# # 	sql_query = """ CREATE TABLE IF NOT EXISTS players (
	# # 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# # 			summoner_name TEXT NOT NULL,
	# # 			summoner_tag TEXT NOT NULL,
	# # 			wins INTEGER DEFAULT 0,
	# # 			loses INTEGER DEFAULT 0,
	# # 			kills INTEGER DEFAULT 0,
	# # 			deaths INTEGER DEFAULT 0,
	# # 			assists INTEGER DEFAULT 0
	# # 		);"""
	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query)
	# # 		self.__conn.commit()
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][__create_players_table] ERROR:  {e}")
	# # 		return False


	# # def get_player(self, summoner_name, summoner_tag):
	# # 	sql_query = "SELECT * FROM players WHERE summoner_name = ? AND summoner_tag = ?;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (summoner_name, summoner_tag))
	# # 		row = cursor.fetchone()
	# # 		if row is None:
	# # 			if self.__DEBUG:
	# # 				print(f"[-][CUSTOMS_DB][get_player] Could not find player {summoner_name}#{summoner_tag} :(")
	# # 			return None
	# # 		else:
	# # 			if self.__DEBUG:
	# # 				print(f"[+][CUSTOMS_DB][get_player] Found player {summoner_name}#{summoner_tag} :)")
	# # 			return row
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][get_player] ERROR: {e}")
	# # 		return None


	# # def register_player(self, summoner_name, summoner_tag):
	# # 	sql_query = "INSERT INTO players (summoner_name, summoner_tag) VALUES (?, ?);"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (summoner_name, summoner_tag))
	# # 		self.__conn.commit()
	# # 		if self.__DEBUG:
	# # 			print(f"[+][CUSTOMS_DB][register_player] Successfully registered player {summoner_name}#{summoner_tag} :D")
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][regiter_player] ERROR: {e}")
	# # 		return False

	# # def update_player(self, summoner_name, summoner_tag, wins, loses, kills, deaths, assists):
	# # 	sql_query = f"UPDATE players SET wins = ?, loses = ?, kills = ?, deaths = ?, assists = ?  WHERE summoner_name = ? AND summoner_tag = ?;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (wins, loses, kills, deaths, assists, summoner_name, summoner_tag))
	# # 		self.__conn.commit()
	# # 		if self.__DEBUG:
	# # 			print(f"[+][CUSTOMS_DB][update_player] Successfully updated player details for {summoner_name}#{summoner_tag} :D")
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][update_player] ERROR: {e}")
	# # 		return False

	# ##########
	# # EVENTS #
	# ##########
	# # THIS TABLE MAY BE UNNECESSARY BUT WILL KEEP IT HERE FOR NOW
	# # def __create_game_events_table(self):
	# # 	sql_query = """ CREATE TABLE IF NOT EXISTS game_events (
	# # 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# # 			game_id TEXT NOT NULL,
	# # 			game_event_id INTEGER NOT NULL,
	# # 			game_event_data TEXT NOT NULL
	# # 		);"""
	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query)
	# # 		self.__conn.commit()
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][__create_game_events_table] ERROR: {e}")
	# # 		return False


	# # def get_game_events_by_game_id(self, game_id):
	# # 	sql_query = "SELECT * FROM game_events WHERE game_id = ?;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (game_id,))
	# # 		row = cursor.fetchall()
	# # 		if row is None:
	# # 			if self.__DEBUG:
	# # 				print(f"[-][CUSTOMS_DB][get_game_events_by_game_id] Could not find game events associated with game id {game_id} :(")
	# # 			return None
	# # 		else:
	# # 			if self.__DEBUG:
	# # 				print(f"[+][CUSTOMS_DB][get_game_events_by_game_id] Found {str(len(row))} records associated with game id {game_id} :)")
	# # 			return row
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][get_game_events_by_game_id] ERROR: {e}")
	# # 		return None


	# # def insert_game_event(self, game_id, game_event_id, game_event_data):
	# # 	sql_query = "INSERT INTO game_events (game_id, game_event_id, game_event_data) VALUES (?, ?, ?);"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (game_id, game_event_id, game_event_data))
	# # 		self.__conn.commit()
	# # 		if self.__DEBUG:
	# # 			print(f"[+][CUSTOMS_DB][insert_game_event] Successfully inserted game event for game {game_id} :D")
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][insert_game_event] ERROR: {e}")
	# # 		return False


	# ################
	# # GAME HISTORY #
	# ################
	# def __create_game_data_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS game_data (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			game_id TEXT NOT NULL UNIQUE,
	# 			game_data_blob BLOB NOT NULL
	# 		);"""

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_game_data_table] ERROR: {e}")
	# 		return False


	# def get_total_games(self):
	# 	sql_query = "SELECT COUNT(*) FROM game_data;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		row = cursor.fetchone()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_total_games] No games found :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_total_games] Found {str(row[0])} games!")
	# 			return row[0]
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_total_games] ERROR: {e}")
	# 		return None


	# # def get_all_game_data(self):
	# # 	sql_query = "SELECT * FROM game_data;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query)
	# # 		row = cursor.fetchall()
	# # 		if row is None:
	# # 			if self.__DEBUG:
	# # 				print(f"[-][CUSTOMS_DB][get_all_game_data] No game history found :(")
	# # 			return None
	# # 		else:
	# # 			if self.__DEBUG:
	# # 				print(f"[+][CUSTOMS_DB][get_all_game_data] Found {str(len(row))} game(s) history!")
	# # 			return row
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][get_all_game_data] ERROR: {e}")
	# # 		return None


	# def get_game_data_blob_by_game_id(self, game_id):
	# 	sql_query = "SELECT game_data_blob FROM game_data WHERE game_id = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(game_id),))
	# 		row = cursor.fetchone()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_game_data_blob_by_game_id] Could not find any game with game id {game_id} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_game_data_blob_by_game_id] Found game id {str(game_id)} :D")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_game_data_blob_by_game_id] ERROR: {e}")
	# 		return None

	# # def get_game_data_by_team_uuid(self, team_uuid):
	# # 	sql_query = "SELECT * FROM game_data WHERE team_uuid = ?;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (str(team_uuid),))
	# # 		row = cursor.fetchall()
	# # 		if row is None:
	# # 			if self.__DEBUG:
	# # 				print(f"[-][CUSTOMS_DB][get_game_data_by_team_uuid] Could not find any game history :(")
	# # 			return None
	# # 		else:
	# # 			if self.__DEBUG:
	# # 				print(f"[+][CUSTOMS_DB][get_game_data_by_team_uuid] Found {str(len(row))} game(s) history for team {str(team_uuid)} :D")
	# # 			return row
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][get_game_data_by_team_uuid] ERROR: {e}")
	# # 		return None


	# def add_game(self, game_id, game_data_blob):
	# 	sql_query = f"INSERT INTO game_data (game_id, game_data_blob) VALUES (?, ?);"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (game_id, game_data_blob))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][add_game] Successfully added game id {game_id} :)")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][add_game] ERROR: {e}")
	# 		return False


	# # def update_end_game_data(self, game_id, game_data):
	# # 	# get current timestamp
	# # 	current_timestamp = datetime.datetime.now()

	# # 	sql_query = f"UPDATE game_data SET game_data = ?, game_state = 'COMPLETE', last_updated = ? WHERE game_id = ?;"

	# # 	try:
	# # 		cursor = self.__conn.cursor()
	# # 		cursor.execute(sql_query, (game_data, current_timestamp, game_id))
	# # 		self.__conn.commit()
	# # 		if self.__DEBUG:
	# # 			print(f"[+][CUSTOMS_DB][update_end_game_data] Successfully updated end game details for game id {game_id} :D")
	# # 		return True
	# # 	except Error as e:
	# # 		print(f"[!][CUSTOMS_DB][update_end_game_data] ERROR: {e}")
	# # 		return False


	# ###############
	# # team_games #
	# ###############
	# def __create_team_games_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS team_games (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			team_uuid TEXT NOT NULL,
	# 			game_id TEXT NOT NULL,
	# 			FOREIGN KEY(team_uuid) REFERENCES teams(team_uuid),
	# 			FOREIGN KEY(game_id) REFERENCES game_data(game_id)
	# 		);"""

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_team_games_table] ERROR: {e}")
	# 		return False
		
	# def get_total_team_games(self):
	# 	sql_query = "SELECT COUNT(*) FROM team_games;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		row = cursor.fetchone()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_total_team_games] No team games found :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_total_team_games] Found {str(row[0])} games!")
	# 			return row[0]
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_total_team_games] ERROR: {e}")
	# 		return None

	# def add_team_game(self, team_uuid, game_id):
	# 	sql_query = "INSERT INTO team_games (team_uuid, game_id) VALUES (?, ?);"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid), game_id))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][add_team_game] Successfully added game id {game_id} to team {team_uuid} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][add_team_game] ERROR: {e}")
	# 		return False
		
	# def remove_team_game(self, team_uuid, game_id):
	# 	sql_query = "DELETE FROM team_games WHERE team_uuid = ? AND game_id = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid), game_id))
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][remove_team_game] ERROR: {e}")
	# 		return False

	# def get_team_game_id_data_by_team_uuid(self, team_uuid):
	# 	sql_query = """
	# 		SELECT gd.game_id
	# 		FROM game_data gd
	# 		JOIN team_games tg ON gd.game_id = tg.game_id
	# 		WHERE tg.team_uuid = ?;
	# 	"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid),))
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] Could not find any game data for team {team_uuid} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] Found {str(len(row))} game(s) for team {team_uuid} :D")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] ERROR: {e}")
	# 		return None

	# def get_team_game_data_by_team_uuid(self, team_uuid):
	# 	sql_query = """
	# 		SELECT gd.game_id, gd.game_data_blob
	# 		FROM game_data gd
	# 		JOIN team_games tg ON gd.game_id = tg.game_id
	# 		WHERE tg.team_uuid = ?;
	# 	"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid),))
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_team_game_data_by_team_uuid] Could not find any game data for team {team_uuid} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_team_game_data_by_team_uuid] Found {str(len(row))} game(s) for team {team_uuid} :D")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_team_game_data_by_team_uuid] ERROR: {e}")
	# 		return None

	# def check_if_team_game_exists(self, game_id, team_uuid):
	# 	sql_query = "SELECT * FROM team_games WHERE game_id = ? AND team_uuid = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (game_id, str(team_uuid)))
	# 		row = cursor.fetchone()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][check_if_team_game_exists] Game {game_id} does not exist for team {team_uuid}")
	# 			return False
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][check_if_team_game_exists] Game {game_id} exists for team {team_uuid} :)")
	# 			return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][check_if_team_game_exists] ERROR: {e}")
	# 		return False

	# ##########
	# # PATCH  #
	# ##########
	# def __create_current_patch_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS current_patch (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			patch_version TEXT NOT NULL
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()

	# 		 # Check if there is already a record in the table
	# 		cursor.execute("SELECT COUNT(*) FROM current_patch;")
	# 		count = cursor.fetchone()[0]

	# 		# Insert initial record if the table is empty
	# 		if count == 0:
	# 			sql_query = "INSERT INTO current_patch (patch_version) VALUES (?);"
	# 			cursor.execute(sql_query, ("0.0.0",))
	# 			self.__conn.commit()

	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_current_patch_table] ERROR: {e}")
	# 		return False

	# def get_current_patch(self):
	# 	sql_query = "SELECT patch_version FROM current_patch ORDER BY id DESC LIMIT 1;"
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		row = cursor.fetchone()
	# 		if row:
	# 			return row[0]
	# 		else:
	# 			return None
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_current_patch] ERROR: {e}")
	# 		return None

	# #########################
	# # SUMMONER DATA PRIVACY #
	# #########################
	# def __create_summoner_data_privacy_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS summoner_data_privacy (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			riot_id TEXT NOT NULL,
	# 			team_uuid TEXT NOT NULL
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_summoner_data_privacy_table] ERROR: {e}")
	# 		return False
		
	# def get_team_data_removed_users(self, team_uuid):
	# 	sql_query = "SELECT riot_id FROM summoner_data_privacy WHERE team_uuid = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid),))
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_team_data_removed_users] Could not find any users for team {team_uuid} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_team_data_removed_users] Found {str(len(row))} users for team {team_uuid} :D")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_team_data_removed_users] ERROR: {e}")
	# 		return None

	# def add_user_to_removed_data(self, riot_id, team_uuid):
	# 	sql_query = "INSERT INTO summoner_data_privacy (riot_id, team_uuid) VALUES (?, ?);"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (riot_id, str(team_uuid)))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][add_user_to_removed_data] Successfully added user {riot_id} to team {team_uuid} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][add_user_to_removed_data] ERROR: {e}")
	# 		return False
		
	# def remove_user_from_removed_data(self, riot_id, team_uuid):
	# 	sql_query = "DELETE FROM summoner_data_privacy WHERE riot_id = ? AND team_uuid = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (riot_id, str(team_uuid)))
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][remove_user_from_removed_data] ERROR: {e}")
	# 		return False