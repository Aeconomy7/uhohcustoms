import sqlite3
import datetime

from sqlite3 import Error

class CustomsDbHandler:
	def __init__(self):
		self.__db_location = "customs_sqlite.db"

		# Create connection for initiating tables
		self.__conn = self.__create_connection(self.__db_location)
		if self.__conn is None:
			print("[-] Could not connect to Customs DB")
			return

		# Create tables if not exist
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

	def __create_player_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS player_info (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				summoner_name TEXT NOT NULL,
				summoner_tag TEXT NOT NULL,
				puuid TEXT NOT NULL,
				wins INTEGER DEFAULT 0,
				loses INTEGER DEFAULT 0,
				kills INTEGER DEFAULT 0,
				deaths INTEGER DEFAULT 0,
				assists INTEGER DEFAULT 0
			);"""

	def __create_game_history_table(self):
		sql_query = """ CREATE TABLE IF NOT EXISTS customs_history (
				id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
				game_id TEXT NOT NULL,
				game_data TEXT NOT NULL
			);"""

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
		except Error as e:
			print(e)

	def get_match_history(self):
		sql_query = "SELECT * FROM customs_history"

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchall()
			if row is None:
				print("[-] Could not find any match history :(")
				return None
			else:
				print("[+] Found match history! :D")
				return row
		except Error as e:
			print(e)
			return None

	def insert_match(self, match_id, tournament_id, game_id, winning_team, losing_team, metadata):
		# get current timestamp
		current_timestamp = datetime.datetime.now()

		sql_query = f"INSERT INTO customs_history (match_id, tournament_id, game_id, winning_team, losing_team, metadata, game_date) VALUES ('{match_id}', '{tournament_id}', '{game_id}', '{winning_team}', '{losing_team}', '{metadata}', '{current_timestamp}')"

		print("[?] Trying: " + sql_query)

		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			self.__conn.commit()
			print("[+] Successfully inserted match \'" + match_id + "\' :D")
			return True
		except Error as e:
			print(e)
			return False
