import sqlite3
import datetime

from sqlite3 import Error

class CustomsDbHandler:
	def __init__(self):
		self.__db_location = "./db/cs.db"

		# Create connection for initiating tables
		self.__conn = self.__create_connection(self.__db_location)
		if self.__conn is None:
			print("[-] Could not connect to Customs DB")
			return

		# Create tables if not exist
		self.__create_users_table()
		self.__create_teams_table()
		self.__create_players_table()
		self.__create_game_events_table()
		self.__create_game_history_table()
		print("[+] Successfully initiated Customs database tables!")

		# Close connection
		self.__conn.close()

	def __enter__(self):
		#Establish connection with Customs DB
		self.__conn = self.__create_connection(self.__db_location)
		print("[+] Connected to Customs DB")

	def __exit__(self):
		# Commit changes to DB
		self.__conn.commit()
		# Close DB
		self.__conn.close()

	def __create_connection(self,db_file):
		conn = None

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
				team_uuid TEXT NOT NULL
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!] __create_users_table {e}")
			return False


	def get_team_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM teams WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchone()
			if row is None:
				print(f"[-] Team with UUID {team_uuid} does not exist")
				return None
			else:
				print(f"[+] Team with UUID {team_uuid} exists :)")
				return row
		except Error as e:
			print(f"[!] get_user_by_id: {e}")
			return None



	def check_if_team_exists_by_team_name(self, team_name):
		sql_query = "SELECT * FROM teams WHERE team_name = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (team_name,))
			row = cursor.fetchone()
			if row is None:
				print(f"[+] Team {team_name} does not exist")
				return None
			else:
				print(f"[-] Team {team_name} exists :)")
				return row
		except Error as e:
			print(f"[!] check_if_team_exists_by_team_name: {e}")
			return None


	def check_if_team_exists_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM teams WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchone()
			if row is None:
				print(f"[+] Team with uuid {str(team_uuid)} does not exist")
				return None
			else:
				print(f"[-] Team with uuid {str(team_uuid)} exists :)")
				return row
		except Error as e:
			print(f"[!] check_if_team_exists_by_team_uuid: {e}")
			return None



	def register_team(self, team_name, team_uuid):
		sql_query = "INSERT INTO teams (team_name, team_uuid) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (team_name, str(team_uuid)))
			self.__conn.commit()
			print(f"[+] Successfully registered team {team_name} :D")
			return True
		except Error as e:
			print(f"[!] register_team: {e}")
			return False


	#########
	# USERS #
	#########
	def __create_users_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				username TEXT NOT NULL,
				password_hash TEXT NOT NULL,
				email TEXT NOT NULL,
				team_uuid TEXT NOT NULL DEFAULT 'None'
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!] __create_users_table {e}")
			return False


	def get_user_by_id(self, id):
		sql_query = "SELECT * FROM users WHERE id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (id,))
			row = cursor.fetchone()
			if row is None:
				print(f"[-] User with id {id} does not exist")
				return None
			else:
				print(f"[+] User with id {id} exists :)")
				return row
		except Error as e:
			print(f"[!] get_user_by_id: {e}")
			return None



	def get_user_by_username(self, username):
		sql_query = "SELECT * FROM users WHERE username = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username,))
			row = cursor.fetchone()
			if row is None:
				print(f"[-] User {username} does not exist")
				return None
			else:
				print(f"[+] User {username} exists :)")
				return row
		except Error as e:
			print(f"[!] get_user_by_username: {e}")
			return None

	def get_user_by_email(self, email):
		sql_query = "SELECT * FROM users WHERE email = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (email,))
			row = cursor.fetchone()
			if row is None:
				print(f"[-] User with email {email} does not exist")
				return None
			else:
				print(f"[+] User with email {email} exists :)")
				return row
		except Error as e:
			print(f"[!] get_user_by_email: {e}")
			return None


	def get_users_by_team_uuid(self, team_uuid):
		sql_query = "SELECT username FROM users WHERE team_uuid = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				print(f"[-] Team with uuid {str(team_uuid)} has no users")
				return None
			else:
				print(f"[+] Team with uuid {str(team_uuid)} exists with {str(len(row))} users! :)")
				return row
		except Error as e:
			print(f"[!] get_users_by_team_uuid: {e}")
			return None


	def check_if_user_email_exists(self, username, email):
		sql_query = "SELECT * FROM users WHERE username = ? OR email = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username, email))
			row = cursor.fetchone()
			if row is None:
				print(f"[+] User {username} and email {email} does not exist")
				return None
			else:
				print(f"[-] User {username} or email {email} exists :)")
				return row
		except Error as e:
			print(f"[!] check_if_user_email_exists: {e}")
			return None

	def join_user_to_team(self, username, team_uuid):
		sql_query = "UPDATE users SET team_uuid = ? WHERE username = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid), username))
			self.__conn.commit()
			print(f"[+] Successfully joined user {username} to team {str(team_uuid)} :D")
			return True
		except Error as e:
			print(f"[!] join_user_to_team: {e}")
			return False

	def register_user(self, username, password_hash, email):
		sql_query = "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (username, password_hash, email))
			self.__conn.commit()
			print(f"[+] Successfully registered user {username} :D")
			return True
		except Error as e:
			print(f"[!] register_user: {e}")
			return False


	##########
	# PLAYER #
	##########
	def __create_players_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS players (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				summoner_name TEXT NOT NULL,
				summoner_tag TEXT NOT NULL,
				wins INTEGER DEFAULT 0,
				loses INTEGER DEFAULT 0,
				kills INTEGER DEFAULT 0,
				deaths INTEGER DEFAULT 0,
				assists INTEGER DEFAULT 0
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!] __create_players_table {e}")
			return False


	def get_player(self, summoner_name, summoner_tag):
		sql_query = "SELECT * FROM players WHERE summoner_name = ? AND summoner_tag = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (summoner_name, summoner_tag))
			row = cursor.fetchone()
			if row is None:
				print(f"[-] Could not find player {summoner_name}#{summoner_tag} :(")
				return None
			else:
				print(f"[+] Found player {summoner_name}#{summoner_tag} :)")
				return row
		except Error as e:
			print(f"[!] get_player: {e}")
			return None


	def register_player(self, summoner_name, summoner_tag):
		sql_query = "INSERT INTO players (summoner_name, summoner_tag) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (summoner_name, summoner_tag))
			self.__conn.commit()
			print(f"[+] Successfully registered player {summoner_name}#{summoner_tag} :D")
			return True
		except Error as e:
			print(f"[!] register_player: {e}")
			return False

	def update_player(self, summoner_name, summoner_tag, wins, loses, kills, deaths, assists):
		sql_query = f"UPDATE players SET wins = ?, loses = ?, kills = ?, deaths = ?, assists = ?  WHERE summoner_name = ? AND summoner_tag = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (wins, loses, kills, deaths, assists, summoner_name, summoner_tag))
			self.__conn.commit()
			print(f"[+] Successfully updated player details for {summoner_name}#{summoner_tag} :D")
			return True
		except Error as e:
			print(f"[!] update_player: {e}")
			return False

	##########
	# EVENTS #
	##########
	def __create_game_events_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS game_events (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				game_id TEXT NOT NULL,
				game_event_id INTEGER NOT NULL,
				game_event_data TEXT NOT NULL
			);"""
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!] __create_game_events_table: {e}")
			return False


	def get_game_events_by_game_id(self, game_id):
		sql_query = "SELECT * FROM game_events WHERE game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id,))
			row = cursor.fetchall()
			if row is None:
				print(f"[-] Could not find game events associated with game id {game_id} :(")
				return None
			else:
				print(f"[+] Found {str(len(row))} records associated with game id {game_id} :)")
				return row
		except Error as e:
			print(f"[!] get_game_events_by_game_id: {e}")
			return None


	def insert_game_event(self, game_id, game_event_id, game_event_data):
		sql_query = "INSERT INTO game_events (game_id, game_event_id, game_event_data) VALUES (?, ?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id, game_event_id, game_event_data))
			self.__conn.commit()
			print(f"[+] Successfully inserted game event for game {game_id} :D")
			return True
		except Error as e:
			print(f"[!] insert_game_event: {e}")
			return False


	################
	# GAME HISTORY #
	################
	def __create_game_history_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS game_history (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				game_id TEXT NOT NULL,
				game_data BLOB DEFAULT 'NA',
				game_state TEXT DEFAULT 'ACTIVE',
				team_uuid TEXT NOT NULL,
				last_updated TEXT NOT NULL
			);"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!] __create_game_history_table: {e}")
			return False


	def get_active_games(self):
		sql_query = "SELECT * FROM game_history WHERE game_stata = 'ACTIVE';"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchall()
			if row is None:
				print(f"[-] No active games found :(")
				return None
			else:
				print(f"[+] Found {str(len(row))} active game(s)! :)")
				return row
		except Error as e:
			print(f"[!] get_active_games: {e}")
			return None


	def get_all_game_history(self):
		sql_query = "SELECT * FROM game_history;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchall()
			if row is None:
				print(f"[-] No game history found :(")
				return None
			else:
				print(f"[+] Found {str(len(row))} game(s) history!")
				return row
		except Error as e:
			print(f"[!] get_all_game_history: {e}")
			return None


	def get_game_history_by_game_id(self, game_id):
		sql_query = "SELECT * FROM game_history WHERE game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(game_id),))
			row = cursor.fetchone()
			if row is None:
				print("[-] Could not find any game history :(")
				return None
			else:
				print("[+] Found game id {str(game_id)} :D")
				return row
		except Error as e:
			print(f"[!] get_game_history_by_game_id: {e}")
			return None

	def get_game_history_by_team_uuid(self, team_uuid):
		sql_query = "SELECT * FROM game_history WHERE team_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (str(team_uuid),))
			row = cursor.fetchall()
			if row is None:
				print("[-] Could not find any game history :(")
				return None
			else:
				print("[+] Found {str(len(row))} game(s) history for team {str(team_uuid)} :D")
				return row
		except Error as e:
			print(f"[!] get_game_history_by_team_id: {e}")
			return None


	def register_game(self, game_id):
		current_timestamp = datetime.datetime.now()

		sql_query = f"INSERT INTO game_history (game_id, last_updated) VALUES (?, ?);"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id, current_timestamp))
			self.__conn.commit()
			print(f"[+] Successfully registered game id {game_id} :)")
			return True
		except Error as e:
			print(f"[!] register_game: {e}")
			return False


	def update_end_game_history(self, game_id, game_data):
		# get current timestamp
		current_timestamp = datetime.datetime.now()

		sql_query = f"UPDATE game_history SET game_data = ?, game_state = 'COMPLETE', last_updated = ? WHERE game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_data, current_timestamp, game_id))
			self.__conn.commit()
			print(f"[+] Successfully updated end game details for game id {game_id} :D")
			return True
		except Error as e:
			print(f"[!] update_end_game_history: {e}")
			return False
