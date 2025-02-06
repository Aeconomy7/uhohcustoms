from riotwatcher import LolWatcher, RiotWatcher, ApiError
from urllib.parse import quote
import time
import requests

class RiotAgent:
	def __init__(self, api_key, riot_auth_url, riot_token_url, redirect_uri, server_region="NA1", match_region="AMERICAS"):
		self.__server_region = server_region
		self.__match_region = match_region

		#self.__base_riot_api_url = f"https://{self.__match_region}.api.riotgames.com"
		self.__summoner_api_url = f"/lol/summoner/v4/summoners"
		self.__match_api_url = f"/lol/match/v5/matches"
		
		self.__api_key = api_key

		self.__riot_auth_url = riot_auth_url
		self.__riot_token_url = riot_token_url
		self.__redirect_uri = redirect_uri
		
		# self.__lol_watcher = None
		# self.__riot_watcher = None

		self.__DEBUG = True
		print(f"[?][RIOT_AGENT][__init__] DATADRAGON AGENT DEBUG MODE: {self.__DEBUG}")

		return

	def __enter__(self):
		# self.__lol_watcher = LolWatcher(self.__api_key)
		# self.__riot_watcher = RiotWatcher(self.__api_key)
		if self.__DEBUG:
			print("[+][RIOT_AGENT][__enter__] Connected to Riot API")
		return

	# GETTERS
	def get_lol_watcher(self):
		return self.__lol_watcher
	
	def get_riot_watcher(self):
		return self.__riot_watcher


	# UTILITY FUNCTIONS
	# fetch summoner data
	def fetch_summoner_data(self, summoner_name, match_region, retries=3, timeout=10):
		base_riot_api_url = f"https://{match_region}.api.riotgames.com"
		
		url = f"{base_riot_api_url}{self.__summoner_api_url}/by-name/{quote(summoner_name)}"
		
		headers = {
			"X-Riot-Token": self.__api_key
		}
	
		for attempt in range(retries):
			try:
				response = requests.get(url, headers=headers, timeout=timeout)
				response.raise_for_status()
				return response.json()
			except requests.exceptions.RequestException as e:
				print(f"Error fetching match details: {e}")
				if attempt < retries - 1:
					print(f"Retrying... ({attempt + 1}/{retries})")
					time.sleep(2)
				else:
					raise
				
		return None


	# fetch match data
	def fetch_match_data(self, match_id, match_region, retries=3, timeout=10):
		base_riot_api_url = f"https://{match_region}.api.riotgames.com"
		
		url = f"{base_riot_api_url}{self.__match_api_url}/{match_id}"
		
		headers = {
			"X-Riot-Token": self.__api_key
		}
	
		for attempt in range(retries):
			try:
				response = requests.get(url, headers=headers, timeout=timeout)
				response.raise_for_status()
				return response.json()
			except requests.exceptions.RequestException as e:
				print(f"[-][RIOT_AGENT][fetch_match_data] Error fetching match details: {e}")
				if attempt < retries - 1:
					print(f"[-][RIOT_AGENT][fetch_match_data] Retrying... ({attempt + 1}/{retries})")
					time.sleep(2)
				else:
					raise
				
		return None

	# def fetch_match_data(self, game_id):
	# 	try:
	# 			match = self.__lol_watcher.match.by_id(self.__match_region, game_id)
	# 			return match
	# 	except ApiError as e:
	# 			print(f"Error fetching match details: {e}")
	# 			return None