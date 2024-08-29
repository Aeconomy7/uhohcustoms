import sqlite3
import datetime

from sqlite3 import Error

class CustomsDbHandler:
	def __init__(self):
		self.__db_location = "./db/customs_sqlite.db"

		# Create connection for initiating tables
		self.__conn = self.__create_connection(self.__db_location)
		if self.__conn is None:
			print("[-] Could not connect to Customs DB")
			return

		# Create tables if not exist
		self.__create_players_table()
		self.__create_game_events_table()
		self.__create_game_history_table()
		print("[+] Successfully initiated Customs database!")

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
				assists INTEGER DEFAULT 0,
				flashes INTEGER DEFAULT 0
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
			return True
		except Error as e:
			print(f"[!] register_player: {e}")
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
			cursor.execute(sql_query, (game_id))
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
				game_data TEXT DEFAULT 'NA',
				game_state TEXT DEFAULT 'ACTIVE',
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


	def get_game_history_by_id(self, game_id):
		sql_query = "SELECT * FROM game_history WHERE game_id = ?;"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (game_id))
			row = cursor.fetchone()
			if row is None:
				print("[-] Could not find any game history :(")
				return None
			else:
				print("[+] Found game id {game_id} :D")
				return row
		except Error as e:
			print(f"[!] get_game_history_by_id: {e}")
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
