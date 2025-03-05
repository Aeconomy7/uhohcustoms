# this is an awful file and I want to convert it to sqlalchemy with postgres and sqlite3 support but im not much of a DB architect

import sqlite3
import datetime
import psycopg2
from psycopg2 import sql
from sqlite3 import Error

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from config import DEBUG, SQLITE_DB_PATH

class CustomsDbHandler:
	def __init__(self):
		self.__db_location = SQLITE_DB_PATH

		# DEBUG MODE
		self.__DEBUG = DEBUG
		print(f"[?][CUSTOMS_DB][__init__] DB DEBUG MODE: {self.__DEBUG}")

		# Create connection for initiating tables
		self.__conn = self.__create_connection(self.__db_location)
		if self.__conn is None:
			print("[-][CUSTOMS_DB][__init__] Could not connect to Customs DB")
			return

		# Create tables if not exist
		self.__create_users_table()
		self.__create_teams_table()
		self.__create_user_teams_table()
		#self.__create_players_table()
		#self.__create_game_events_table()
		self.__create_game_data_table()
		self.__create_team_games_table()
		self.__create_current_patch_table()
		self.__create_summoner_data_privacy_table()
		print("[+][CUSTOMS_DB][__init__] Successfully initiated Customs database tables!")

		# Close connection
		self.__conn.close()

	def __enter__(self):
		#Establish connection with Customs DB
		self.__conn = self.__create_connection(self.__db_location)
		print("[+][CUSTOMS_DB][__enter__] Connected to Customs DB")

	def __exit__(self):
		# Commit changes to DB
		self.__conn.commit()
		# Close DB
		self.__conn.close()

	def __create_connection(self,db_file):
		conn = None

		# postgres connection
		# try:
		# 	conn = psycopg2.connect(
		# 		host=DB_HOST,
		# 		port=DB_PORT,
		# 		dbname=DB_NAME,
		# 		user=DB_USER,
		# 		password=DB_PASSWORD
		# 	)
		# 	return conn
		# except psycopg2.Error as e:
		# 	print(f"Error connecting to PostgreSQL database: {e}")
		# 	return None

		# sqlite3 connection
		try:
			conn = sqlite3.connect(db_file)
		except Error as e:
			print(e)

		return conn

	#########
	# TEAMS #
	#########
	def __create_teams_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS teams (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				team_name TEXT NOT NULL,
				team_uuid TEXT NOT NULL UNIQUE,
				team_captain_uuid INTEGER NOT NULL,
				FOREIGN KEY(team_captain_uuid) REFERENCES users(id)
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_users_table] ERROR:  {e}")
			return False


	def get_total_users(self):
		sql_query = "SELECT COUNT(*) FROM users;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_total_users] No users found :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_total_users] Found {str(row[0])} users!")
				return row[0]
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_total_users] ERROR: {e}")
			return None


	def get_team_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM teams WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_team_by_team_uuid] Team with UUID {team_uuid} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_team_by_team_uuid] Team with UUID {team_uuid} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_by_team_uuid] ERROR: {e}")
			return None


	def get_team_members(self, team_uuid):
		sql_query = """
			SELECT
				u.username,
				u.email,
				u.user_uuid,
				CASE WHEN u.user_uuid = t.team_captain_uuid THEN 'Captain' ELSE 'Member' END AS role
			FROM users u
			JOIN user_teams ut ON u.user_uuid = ut.user_uuid
			JOIN teams t ON ut.team_uuid = t.team_uuid
			WHERE t.team_uuid = ?;
		"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][get_team_members] Found {str(len(row))} members of team {str(team_uuid)}")
			return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_members] ERROR: {e}")
			return None


	def get_teams_for_user(self, user_uuid):
		query = """
			SELECT t.team_uuid, t.team_name
			FROM teams t
			JOIN user_teams ut ON t.team_uuid = ut.team_uuid
			JOIN users u ON ut.user_uuid = u.user_uuid
			WHERE u.user_uuid = ?
		"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(query, (str(user_uuid),))
			row = cursor.fetchall()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][get_teams_for_user] Found {str(len(row))} teams for user uuid {user_uuid}")
			return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_teams_for_user] ERROR: {e}")
			return None


	def check_if_team_exists_by_team_name(self, team_name):
		sql_query = "SELECT * FROM teams WHERE team_name = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (team_name,))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][check_if_team_exists_by_team_name] Team {team_name} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][check_if_team_exists_by_team_name] Team {team_name} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][check_if_team_exists_by_team_name] ERROR: {e}")
			return None


	def check_if_team_exists_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM teams WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][check_if_team_exists_by_team_uuid] Team with uuid {str(team_uuid)} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][check_if_team_exists_by_team_uuid] Team with uuid {str(team_uuid)} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][check_if_team_exists_by_team_uuid] ERROR: {e}")
			return None


	def is_user_captain(self, user_uuid):
		sql_query = "SELECT 1 FROM teams WHERE team_captain_uuid = ? LIMIT 1;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid),))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][is_user_captain] User {str(user_uuid)} is not a captain!")
				return None
			else:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][is_user_captain] User {str(user_uuid)} is already a team captain!")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][is_user_captain] ERROR: {e}")
			return None

	def is_user_member_of_team(self, user_uuid, team_uuid):
		sql_query = "SELECT 1 FROM user_teams WHERE user_uuid = ? AND team_uuid = ? LIMIT 1;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][is_user_member_of_team] User {str(user_uuid)} is not a member of team {str(team_uuid)}")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][is_user_member_of_team] User {str(user_uuid)} is a member of team {str(team_uuid)}")
				return row

		except Error as e:
			print(f"[!][CUSTOMS_DB][is_user_member_of_team] ERROR: {e}")
			return None

	def is_user_captain_of_team(self, user_uuid, team_uuid):
		sql_query = "SELECT 1 FROM teams WHERE team_captain_uuid = ? AND team_uuid = ? LIMIT 1;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][is_user_captain_of_team] User {str(user_uuid)} is NOT captain of team {str(team_uuid)}")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][is_user_captain_of_team] User {str(user_uuid)} is captain of team {str(team_uuid)}")
				return row

		except Error as e:
			print(f"[!][CUSTOMS_DB][is_user_captain_of_team] ERROR: {e}")
			return None


	def register_team(self, team_name, team_uuid, team_captain_uuid):
		sql_query = "INSERT INTO teams (team_name, team_uuid, team_captain_uuid) VALUES (?, ?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (team_name, str(team_uuid), str(team_captain_uuid)))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][register_team] Successfully registered team {team_name} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][register_team] ERROR: {e}")
			return False


	#########
	# USERS #
	#########
	def __create_users_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				username TEXT NOT NULL UNIQUE,
				email TEXT NOT NULL UNIQUE,
				user_uuid TEXT NOT NULL UNIQUE,
				password_hash TEXT NOT NULL,
				riot_id TEXT,
				riot_access_token,
				riot_refresh_token
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_users_table] ERROR: {e}")
			return False


	def __create_user_teams_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS user_teams (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				user_uuid TEXT NOT NULL,
				team_uuid TEXT NOT NULL,
				player_score_setting BOOLEAN DEFAULT 0,
				role TEXT NOT NULL DEFAULT 'Pending',
				FOREIGN KEY(user_uuid) REFERENCES users(user_uuid),
				FOREIGN KEY(team_uuid) REFERENCES teams(team_uuid)
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_user_teams_table] ERROR: {e}")
			return False


	def get_total_teams(self):
		sql_query = "SELECT COUNT(*) FROM teams;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_total_teams] No teams found :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_total_teams] Found {str(row[0])} teams!")
				return row[0]
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_total_teams] ERROR: {e}")
			return None


	def get_user_by_id(self, id):
		sql_query = "SELECT * FROM users WHERE id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (id,))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_user_by_id] User with id {id} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_user_by_id] User with id {id} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_user_by_id] ERROR: {e}")
			return None


	def get_user_by_user_uuid(self, user_uuid):
		sql_query = "SELECT * FROM users WHERE user_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid),))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_user_by_user_uuid] User with id {str(user_uuid)} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_user_by_user_uuid] User with id {str(user_uuid)} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_user_by_user_uuid] ERROR: {e}")
			return None


	def get_user_by_username(self, username):
		sql_query = "SELECT * FROM users WHERE username = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username,))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_user_by_username] User {username} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_user_by_username] User {username} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_user_by_username] ERROR: {e}")
			return None


	def get_user_by_email(self, email):
		sql_query = "SELECT * FROM users WHERE email = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (email,))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_user_by_email] User with email {email} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_user_by_email] User with email {email} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_user_by_email] ERROR: {e}")
			return None


	def get_users_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM users WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_users_by_team_uuid] Team with uuid {str(team_uuid)} has no users")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_users_by_team_uuid] Team with uuid {str(team_uuid)} exists with {str(len(row))} users! :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_users_by_team_uuid] ERROR: {e}")
			return None


	def check_if_user_email_exists(self, username, email):
		sql_query = "SELECT * FROM users WHERE username = ? OR email = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username, email))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][check_if_user_email_exists] User {username} and email {email} does not exist")
				return None
			else:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][check_if_user_email_exists] User {username} or email {email} exists :)")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][check_if_user_email_exists] ERROR: {e}")
			return None


	def join_user_to_team(self, user_uuid,  team_uuid, role):
		sql_query = "INSERT INTO user_teams (user_uuid, team_uuid, role) VALUES (?, ?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid), role))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][join_user_to_team] Successfully joined user uuid {str(user_uuid)} to team uuid {str(team_uuid)} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][join_user_to_team] ERROR: {e}")
			return False


	def remove_user_from_team(self, user_uuid, team_uuid):
		sql_query = "DELETE FROM user_teams WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][remove_user_from_team] ERROR: {e}")
			return False


	def register_user(self, username, user_uuid, email, password_hash):
		sql_query = "INSERT INTO users (username, user_uuid, email, password_hash) VALUES (?, ?, ?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username, str(user_uuid), email, password_hash))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][register_user] Successfully registered user {username} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][register_team]: {e}")
			return False
		
	def get_user_team_role(self, user_uuid, team_uuid):
		sql_query = "SELECT role FROM user_teams WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			row = cursor.fetchone()
			if row:
				if self.__DEBUG:
					print(f"[?][CUSTOMS_DB][get_user_team_role] User {str(user_uuid)} is not a PENDING member of team {str(team_uuid)}")
				return row[0]
			else:
				return None
				
		except Error as e:
			print(f"[!][CUSTOMS_DB][check_if_user_is_member_of_team] ERROR: {e}")
			return None

	def approve_user_to_team(self, user_uuid, team_uuid):
		sql_query = "UPDATE user_teams SET role = 'Member' WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][approve_user_to_team] Successfully approved user uuid {str(user_uuid)} to team uuid {str(team_uuid)} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][approve_user_to_team] ERROR: {e}")
			return False
		
	def reject_user_from_team(self, user_uuid, team_uuid):
		sql_query = "DELETE FROM user_teams WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][reject_user_from_team] Successfully rejected user uuid {str(user_uuid)} from team uuid {str(team_uuid)} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][reject_user_from_team] ERROR: {e}")
			return False
		
	def get_all_team_members(self, team_uuid):
		sql_query = """
			SELECT u.username, ut.role, u.user_uuid 
			FROM user_teams ut
			JOIN users u ON ut.user_uuid = u.user_uuid
			WHERE ut.team_uuid = ?;
			"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row:
				if self.__DEBUG:
					print(f"[?][CUSTOMS_DB][get_all_team_members] Found {str(len(row))} members for team {str(team_uuid)}")
				return row
			else:
				return None
				
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_all_team_members] ERROR: {e}")
			return None

	def get_team_members_pending(self, team_uuid):
		sql_query = """
			SELECT u.user_uuid, u.username
			FROM user_teams ut
			JOIN users u ON ut.user_uuid = u.user_uuid
			WHERE ut.team_uuid = ? AND ut.role = 'Pending';
		"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row:
				if self.__DEBUG:
					print(f"[?][CUSTOMS_DB][get_team_members_pending] Found {str(len(row))} pending members for team {str(team_uuid)}")
				return row
			else:
				return None
				
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_members_pending] ERROR: {e}")
			return None
		
	def get_player_score_setting_for_team(self, user_uuid, team_uuid):
		sql_query = "SELECT player_score_setting FROM user_teams WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(user_uuid), str(team_uuid)))
			row = cursor.fetchone()
			if row:
				# if self.__DEBUG:
				# 	print(f"[?][CUSTOMS_DB][get_player_score_setting_for_team] Found player score setting for user {str(user_uuid)} in team {str(team_uuid)}")
				return row[0]
			else:
				return None
				
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_player_score_setting_for_team] ERROR: {e}")
			return None

	def set_player_score_setting_for_team(self, user_uuid, team_uuid, player_score_setting):
		sql_query = "UPDATE user_teams SET player_score_setting = ? WHERE user_uuid = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (player_score_setting, str(user_uuid), str(team_uuid)))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][set_player_score_setting_for_team] Successfully set player score setting to {player_score_setting} for user {str(user_uuid)} in team {str(team_uuid)} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][set_player_score_setting_for_team] ERROR: {e}")
			return False

	###########
	# CONTENT #
	###########
	# def __create_content_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS content (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			content_id TEXT NOT NULL,
	# 			content_category TEXT NOT NULL,
	# 			last_updated_patch TEXT NOT NULL,
	# 			content_path TEXT NOT NULL
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_content_table] ERROR: {e}")
	# 		return False


	##########
	# PLAYER #
	##########
	# def __create_players_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS players (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			summoner_name TEXT NOT NULL,
	# 			summoner_tag TEXT NOT NULL,
	# 			wins INTEGER DEFAULT 0,
	# 			loses INTEGER DEFAULT 0,
	# 			kills INTEGER DEFAULT 0,
	# 			deaths INTEGER DEFAULT 0,
	# 			assists INTEGER DEFAULT 0
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_players_table] ERROR:  {e}")
	# 		return False


	# def get_player(self, summoner_name, summoner_tag):
	# 	sql_query = "SELECT * FROM players WHERE summoner_name = ? AND summoner_tag = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (summoner_name, summoner_tag))
	# 		row = cursor.fetchone()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_player] Could not find player {summoner_name}#{summoner_tag} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_player] Found player {summoner_name}#{summoner_tag} :)")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_player] ERROR: {e}")
	# 		return None


	# def register_player(self, summoner_name, summoner_tag):
	# 	sql_query = "INSERT INTO players (summoner_name, summoner_tag) VALUES (?, ?);"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (summoner_name, summoner_tag))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][register_player] Successfully registered player {summoner_name}#{summoner_tag} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][regiter_player] ERROR: {e}")
	# 		return False

	# def update_player(self, summoner_name, summoner_tag, wins, loses, kills, deaths, assists):
	# 	sql_query = f"UPDATE players SET wins = ?, loses = ?, kills = ?, deaths = ?, assists = ?  WHERE summoner_name = ? AND summoner_tag = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (wins, loses, kills, deaths, assists, summoner_name, summoner_tag))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][update_player] Successfully updated player details for {summoner_name}#{summoner_tag} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][update_player] ERROR: {e}")
	# 		return False

	##########
	# EVENTS #
	##########
	# THIS TABLE MAY BE UNNECESSARY BUT WILL KEEP IT HERE FOR NOW
	# def __create_game_events_table(self):
	# 	sql_query = """ CREATE TABLE IF NOT EXISTS game_events (
	# 			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	# 			game_id TEXT NOT NULL,
	# 			game_event_id INTEGER NOT NULL,
	# 			game_event_data TEXT NOT NULL
	# 		);"""
	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		self.__conn.commit()
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][__create_game_events_table] ERROR: {e}")
	# 		return False


	# def get_game_events_by_game_id(self, game_id):
	# 	sql_query = "SELECT * FROM game_events WHERE game_id = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (game_id,))
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_game_events_by_game_id] Could not find game events associated with game id {game_id} :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_game_events_by_game_id] Found {str(len(row))} records associated with game id {game_id} :)")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_game_events_by_game_id] ERROR: {e}")
	# 		return None


	# def insert_game_event(self, game_id, game_event_id, game_event_data):
	# 	sql_query = "INSERT INTO game_events (game_id, game_event_id, game_event_data) VALUES (?, ?, ?);"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (game_id, game_event_id, game_event_data))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][insert_game_event] Successfully inserted game event for game {game_id} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][insert_game_event] ERROR: {e}")
	# 		return False


	################
	# GAME HISTORY #
	################
	def __create_game_data_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS game_data (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				game_id TEXT NOT NULL UNIQUE,
				game_data_blob BLOB NOT NULL
			);"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_game_data_table] ERROR: {e}")
			return False


	def get_total_games(self):
		sql_query = "SELECT COUNT(*) FROM game_data;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_total_games] No games found :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_total_games] Found {str(row[0])} games!")
				return row[0]
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_total_games] ERROR: {e}")
			return None


	# def get_all_game_data(self):
	# 	sql_query = "SELECT * FROM game_data;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query)
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_all_game_data] No game history found :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_all_game_data] Found {str(len(row))} game(s) history!")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_all_game_data] ERROR: {e}")
	# 		return None


	def get_game_data_blob_by_game_id(self, game_id):
		sql_query = "SELECT game_data_blob FROM game_data WHERE game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(game_id),))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_game_data_blob_by_game_id] Could not find any game with game id {game_id} :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_game_data_blob_by_game_id] Found game id {str(game_id)} :D")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_game_data_blob_by_game_id] ERROR: {e}")
			return None

	# def get_game_data_by_team_uuid(self, team_uuid):
	# 	sql_query = "SELECT * FROM game_data WHERE team_uuid = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (str(team_uuid),))
	# 		row = cursor.fetchall()
	# 		if row is None:
	# 			if self.__DEBUG:
	# 				print(f"[-][CUSTOMS_DB][get_game_data_by_team_uuid] Could not find any game history :(")
	# 			return None
	# 		else:
	# 			if self.__DEBUG:
	# 				print(f"[+][CUSTOMS_DB][get_game_data_by_team_uuid] Found {str(len(row))} game(s) history for team {str(team_uuid)} :D")
	# 			return row
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][get_game_data_by_team_uuid] ERROR: {e}")
	# 		return None


	def add_game(self, game_id, game_data_blob):
		sql_query = f"INSERT INTO game_data (game_id, game_data_blob) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id, game_data_blob))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][add_game] Successfully added game id {game_id} :)")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][add_game] ERROR: {e}")
			return False


	# def update_end_game_data(self, game_id, game_data):
	# 	# get current timestamp
	# 	current_timestamp = datetime.datetime.now()

	# 	sql_query = f"UPDATE game_data SET game_data = ?, game_state = 'COMPLETE', last_updated = ? WHERE game_id = ?;"

	# 	try:
	# 		cursor = self.__conn.cursor()
	# 		cursor.execute(sql_query, (game_data, current_timestamp, game_id))
	# 		self.__conn.commit()
	# 		if self.__DEBUG:
	# 			print(f"[+][CUSTOMS_DB][update_end_game_data] Successfully updated end game details for game id {game_id} :D")
	# 		return True
	# 	except Error as e:
	# 		print(f"[!][CUSTOMS_DB][update_end_game_data] ERROR: {e}")
	# 		return False


	###############
	# team_games #
	###############
	def __create_team_games_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS team_games (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				team_uuid TEXT NOT NULL,
				game_id TEXT NOT NULL,
				FOREIGN KEY(team_uuid) REFERENCES teams(team_uuid),
				FOREIGN KEY(game_id) REFERENCES game_data(game_id)
			);"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_team_games_table] ERROR: {e}")
			return False
		
	def get_total_team_games(self):
		sql_query = "SELECT COUNT(*) FROM team_games;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_total_team_games] No team games found :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_total_team_games] Found {str(row[0])} games!")
				return row[0]
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_total_team_games] ERROR: {e}")
			return None

	def add_team_game(self, team_uuid, game_id):
		sql_query = "INSERT INTO team_games (team_uuid, game_id) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid), game_id))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][add_team_game] Successfully added game id {game_id} to team {team_uuid} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][add_team_game] ERROR: {e}")
			return False
		
	def remove_team_game(self, team_uuid, game_id):
		sql_query = "DELETE FROM team_games WHERE team_uuid = ? AND game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid), game_id))
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][remove_team_game] ERROR: {e}")
			return False

	def get_team_game_id_data_by_team_uuid(self, team_uuid):
		sql_query = """
			SELECT gd.game_id
			FROM game_data gd
			JOIN team_games tg ON gd.game_id = tg.game_id
			WHERE tg.team_uuid = ?;
		"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] Could not find any game data for team {team_uuid} :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] Found {str(len(row))} game(s) for team {team_uuid} :D")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_game_id_data_by_team_uuid] ERROR: {e}")
			return None

	def get_team_game_data_by_team_uuid(self, team_uuid):
		sql_query = """
			SELECT gd.game_id, gd.game_data_blob
			FROM game_data gd
			JOIN team_games tg ON gd.game_id = tg.game_id
			WHERE tg.team_uuid = ?;
		"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_team_game_data_by_team_uuid] Could not find any game data for team {team_uuid} :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_team_game_data_by_team_uuid] Found {str(len(row))} game(s) for team {team_uuid} :D")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_game_data_by_team_uuid] ERROR: {e}")
			return None

	def check_if_team_game_exists(self, game_id, team_uuid):
		sql_query = "SELECT * FROM team_games WHERE game_id = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id, str(team_uuid)))
			row = cursor.fetchone()
			if row is None:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][check_if_team_game_exists] Game {game_id} does not exist for team {team_uuid}")
				return False
			else:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][check_if_team_game_exists] Game {game_id} exists for team {team_uuid} :)")
				return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][check_if_team_game_exists] ERROR: {e}")
			return False

	##########
	# PATCH  #
	##########
	def __create_current_patch_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS current_patch (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				patch_version TEXT NOT NULL
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()

			 # Check if there is already a record in the table
			cursor.execute("SELECT COUNT(*) FROM current_patch;")
			count = cursor.fetchone()[0]

			# Insert initial record if the table is empty
			if count == 0:
				sql_query = "INSERT INTO current_patch (patch_version) VALUES (?);"
				cursor.execute(sql_query, ("0.0.0",))
				self.__conn.commit()

			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_current_patch_table] ERROR: {e}")
			return False

	def get_current_patch(self):
		sql_query = "SELECT patch_version FROM current_patch ORDER BY id DESC LIMIT 1;"
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row:
				return row[0]
			else:
				return None
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_current_patch] ERROR: {e}")
			return None
	


	#########################
	# SUMMONER DATA PRIVACY #
	#########################
	def __create_summoner_data_privacy_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS summoner_data_privacy (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				riot_id TEXT NOT NULL,
				team_uuid TEXT NOT NULL
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][__create_summoner_data_privacy_table] ERROR: {e}")
			return False
		
	def get_team_data_removed_users(self, team_uuid):
		sql_query = "SELECT riot_id FROM summoner_data_privacy WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				if self.__DEBUG:
					print(f"[-][CUSTOMS_DB][get_team_data_removed_users] Could not find any users for team {team_uuid} :(")
				return None
			else:
				if self.__DEBUG:
					print(f"[+][CUSTOMS_DB][get_team_data_removed_users] Found {str(len(row))} users for team {team_uuid} :D")
				return row
		except Error as e:
			print(f"[!][CUSTOMS_DB][get_team_data_removed_users] ERROR: {e}")
			return None

	def add_user_to_removed_data(self, riot_id, team_uuid):
		sql_query = "INSERT INTO summoner_data_privacy (riot_id, team_uuid) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (riot_id, str(team_uuid)))
			self.__conn.commit()
			if self.__DEBUG:
				print(f"[+][CUSTOMS_DB][add_user_to_removed_data] Successfully added user {riot_id} to team {team_uuid} :D")
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][add_user_to_removed_data] ERROR: {e}")
			return False
		
	def remove_user_from_removed_data(self, riot_id, team_uuid):
		sql_query = "DELETE FROM summoner_data_privacy WHERE riot_id = ? AND team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (riot_id, str(team_uuid)))
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][CUSTOMS_DB][remove_user_from_removed_data] ERROR: {e}")
			return False