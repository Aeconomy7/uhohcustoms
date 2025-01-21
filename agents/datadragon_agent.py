import requests
import tarfile
import os
import json
import base64
import sqlite3
from sqlite3 import Error

class DataDragonAgent:
	# DEFAULT CONSTRUCTOR
	def __init__(self):
		self.__base_dd_url = "https://ddragon.leagueoflegends.com"
		self.__local_dd_path = "./static/dd"
		self.__db_location = "./db/cs.db"

		# DEBUG MODE
		self.__DEBUG = True
		print(f"[?][DD_AGENT][__init__] DATADRAGON AGENT DEBUG MODE: {self.__DEBUG}")
		

	def __enter__(self):
		#Establish connection with Customs DB
		self.__conn = self.__create_connection(self.__db_location)
		print("[+][DD_AGENT][__enter__] Connected DataDragon to Customs DB")
		self.update_current_patch()
		self.__current_patch = self.get_current_patch_from_db()
		if self.__current_patch:
			print(f"[+][DD_AGENT][__enter__] Current patch in DB: {self.__current_patch}")
		else:
			print("[-][DD_AGENT][__enter__] No current patch in DB, updating now...")
			self.__current_patch = self.update_current_patch()


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
	
	# GETTERS
	def get_current_patch(self):
		return self.__current_patch

	# DB FUNCTIONS
	def get_current_patch_from_db(self):
		sql_query = "SELECT patch_version FROM current_patch ORDER BY id DESC LIMIT 1;"
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query)
			row = cursor.fetchone()
			if row:
				self.__current_patch = row[0]
				return row[0]
			else:
				return None
		except Error as e:
			print(f"[!][DD_AGENT][get_current_patch_in_db] get_current_patch_from_db: {e}")
			return None


	def set_current_patch_in_db(self, patch_version):
		sql_query = "UPDATE current_patch SET patch_version = ? WHERE id = 1;"
		try:
			cursor = self.__conn.cursor()
			cursor.execute(sql_query, (patch_version,))
			self.__conn.commit()
			return True
		except Error as e:
			print(f"[!][DD_AGENT][set_current_patch_in_db] set_current_patch_in_db: {e}")
			return False

	# UTILITY FUNCTIONS
	# UPDATE CURRENT PATCH BASED ON RIOT
	def update_current_patch(self):
		url = f'{self.__base_dd_url}/api/versions.json'
		response = requests.get(url)
		if response.status_code == 200:
			versions = response.json()
			if len(versions) > 0:
				current_patch = versions[0]
				if current_patch == self.get_current_patch_from_db():
					self.__current_patch = current_patch
					print(f"[+][DD_AGENT][update_current_patch] Current patch is already up to date: {current_patch}")
					return current_patch
				else:
					self.set_current_patch_in_db(current_patch)
					self.__current_patch = current_patch
					self.download_and_extract_archive()
					print(f"[+][DD_AGENT][update_current_patch] Successfully updated current patch to {current_patch} and downloaded the archive.")
					return current_patch
			else:
				print("[-][DD_AGENT][update_current_patch] No versions found in the response.")
				return None
		else:
			print(f"[-][DD_AGENT][update_current_patch] Failed to fetch versions: {response.status_code}")
			return None

	# DOWNLOAD NEWEST DATA DRAGON ARCHIVE AND EXTRACT IT
	def download_and_extract_archive(self):
		url = f'{self.__base_dd_url}/cdn/dragontail-{self.__current_patch}.tgz'
		local_archive_path = f'./static/dd/archives/dragontail-{self.__current_patch}.tgz'
		extract_path = f'./static/dd/{self.__current_patch}'

		 # Check if the folder already exists
		if os.path.exists(extract_path):
			print(f"[+][DD_AGENT][download_and_extract_archive] Folder already exists: {extract_path}")
			return

		# Download the archive
		response = requests.get(url, stream=True)
		if response.status_code == 200:
			with open(local_archive_path, 'wb') as file:
				for chunk in response.iter_content(chunk_size=1024):
					file.write(chunk)
			print(f"[+][DD_AGENT][download_and_extract_archive] Successfully downloaded archive: {local_archive_path}")

			# Extract the archive
			if tarfile.is_tarfile(local_archive_path):
				with tarfile.open(local_archive_path, 'r:gz') as tar:
					tar.extractall(path=extract_path)
				print(f"[+][DD_AGENT][download_and_extract_archive] Successfully extracted archive to: {extract_path}")
			else:
				print("[-][DD_AGENT][download_and_extract_archive] The downloaded file is not a valid tar archive.")
		else:
			print(f"[-][DD_AGENT][download_and_extract_archive] Failed to download archive: {response.status_code}")

	# FETCH METADATA FOR IMAGES
	def fetch_metadata(self):
		# Fetch metadata for champions, items, and spells
		champions_path = f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/data/en_US/champion.json"
		items_path = f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/data/en_US/item.json"
		spells_path = f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/data/en_US/summoner.json"

		# Load JSON data from local files
		with open(champions_path, 'r') as champions_file:
			champions_data = json.load(champions_file)
		
		with open(items_path, 'r') as items_file:
			items_data = json.load(items_file)
		
		with open(spells_path, 'r') as spells_file:
			spells_data = json.load(spells_file)

		return champions_data, items_data, spells_data

	def get_images_by_category(self, category):
		champions_data, items_data, spells_data = self.fetch_metadata()

		def convert_image_to_base64(image_path):
			with open(image_path, "rb") as image_file:
				return base64.b64encode(image_file.read()).decode('utf-8')

		if category == 'champion':
			return [{"image_base64": convert_image_to_base64(f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/champion/{champion['image']['full']}"), "champion_name": champion['name']} for champion in champions_data['data'].values()]
		elif category == 'item':
			return [{"image_base64": convert_image_to_base64(f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/item/{item['image']['full']}"), "item_name": item['name']} for item in items_data['data'].values()]
		elif category == 'spell':
			return [{"image_base64": convert_image_to_base64(f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/spell/{spell['image']['full']}"), "spell_name": spell['name']} for spell in spells_data['data'].values()]
		else:
			return []

		# if category == 'champion':
		# 	return [{"image_path": f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/champion/{champion['image']['full']}", "champion_name": champion['name']} for champion in champions_data['data'].values()]
		# elif category == 'item':
		# 	return [{"image_path": f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/item/{item['image']['full']}", "item_name": item['name']} for item in items_data['data'].values()]
		# elif category == 'spell':
		# 	return [{"image_path": f"{self.__local_dd_path}/{self.__current_patch}/{self.__current_patch}/img/spell/{spell['image']['full']}", "spell_name": spell['name']} for spell in spells_data['data'].values()]
		# else:
		# 	return []