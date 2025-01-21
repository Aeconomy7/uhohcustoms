import requests
import sqlite3

class DataDragonAgent:
	
	def __init__(self):
		self.__current_patch = requests.get('https://ddragon.leagueoflegends.com/api/versions.json').json()[0]
		self.__db_location = "./db/cs.db"

		# DEBUG MODE
		self.__DEBUG = True
		print(f"[?] DATADRAGON DEBUG MODE: {self.__DEBUG}")

		# Create connection for initiating tables
		self.__conn = self.__create_connection(self.__db_location)
		if self.__conn is None:
			print("[-] Could not connect to Customs DB")
			return

		# Create tables if not exist
		print("[+] Successfully initiated Customs database tables!")

		# Close connection
		self.__conn.close()


	def close_connection(self):
		self.conn.close()
