import requests
import datetime
import time
import socket
import sys
import io
import json
from config import LOCAL_HOST, LOCAL_PORT, LC_EVENT_URL, CUSTOMS_HOST, CUSTOMS_PORT, CUSTOMS_DATA_CALLBACK, RIOT_API_KEY, SECRET_HEADER


################### GLOBALS ###################
CUSTOMS_SERVER_STATUS = False # tracks if uhohcustoms is online, True if it is, False if it isnt
PLAYERS_DATA = []
#LC_PROXIES = None
#WEB_PROXIES = None
LC_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }
WEB_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }


################### UTILITY FUNCTIONS ###################
def get_event_headers(event_type):
	return {
		"Content-Type": "application/json",
		"X-Agent-Secret": SECRET_HEADER,
		"X-Event-Type": event_type
	}


################### NETWORK STUFF ###################
def wait_for_port(host, port):
	while not is_port_open(host, port):
		#print(f"[-] Port {port} is not open. Retrying...")
		time.sleep(1)  # Wait for 2 seconds before retrying

	print(f"[+] Port {port} is now open, commence game!")
	return


def is_port_open(host, port):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		#print(f"[?] Trying {host}:{port} ...")
		sock.settimeout(1)  # Set a timeout for the connection attempt
		result = sock.connect_ex((host, port))
		return result == 0  # Return True if the port is open


################### LIVE CLIENT API ###################
def execute_game():
	# Global variable declarations
	global CUSTOMS_SERVER_STATUS
	global PLAYERS_DATA

	event_id = 0
	file_path = f"./{str(int(time.time()))}_game.txt"
		
	# open log file
	with open(file_path, 'x', encoding='utf-8') as file:
		# Get game data to fetch players
		while True:
			try:
				gamedata_response = requests.get(LC_EVENT_URL + "/allgamedata", verify=False, timeout=2, proxies=LC_PROXIES)
				gamedata_response.raise_for_status()
				
				gamedata = gamedata_response.json()
				print(f"[?] Players in game and their champs:")
				
				for p in gamedata['allPlayers']:
					#print("[?] player: " + str(player))
					#players.append(json.dumps(player))
					player = {
						'player_name':	p['riotId'],
						'champion':		p['championName'],
						'team':			p['team'],
						#'kills':		p['scores']['kills'],
						#'deaths':		p['scores']['deaths'],
						#'assists':		p['scores']['assists']
						'kills':		0,
						'deaths':		0,
						'assists':		0
					}
					PLAYERS_DATA.append(player)
					print(f"\t|-> {player['team']} player_info: " + str(player))
					file.write(str(player) + '\n')

				break
				
			except requests.exceptions.Timeout:
				print(f"[!] Gamedata request timed out.")
				time.sleep(1)
				continue
			except requests.exceptions.RequestException as e:
				print(f"[!] Gamedata Request failed: {e}")
				time.sleep(1)
				continue
		
		# Send player data to uhohcustoms if its running	
		if CUSTOMS_SERVER_STATUS == True:
			try:
				callback_response = requests.post(CUSTOMS_DATA_CALLBACK, json=PLAYERS_DATA, headers=get_event_headers("PLAYER_DATA"), verify=False, timeout=2, proxies=WEB_PROXIES)
				callback_response.raise_for_status()
			except requests.exceptions.Timeout:
				print(f"[!] Callback request timed out.")
			except requests.exceptions.RequestException as e:
				print(f"[!] Request failed: {e}")
				
		# START THE GAME EVENT LOOP
		while True:
			try:
				response = requests.get(LC_EVENT_URL + "/eventdata?eventID=" + str(event_id), verify=False, timeout=2, proxies=LC_PROXIES)
				response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

				event_data = response.json()

				if isinstance(event_data['Events'], list):
					for index, event in enumerate(event_data['Events']):
						# print message to file for tracking
						try:
							file.write(str(event) + '\n')
						except UnicodeEncodeError as e:
							print(f"[!] Encoding error while printing event data: {e}")

						if CUSTOMS_SERVER_STATUS == True:
							try:
								callback_response = requests.post(CUSTOMS_DATA_CALLBACK, data=json.dumps(event), headers=get_event_headers("EVENT_DATA"), verify=False, timeout=2, proxies=WEB_PROXIES)
								callback_response.raise_for_status()
							except requests.exceptions.Timeout:
								print(f"[!] Callback request timed out.")
							except requests.exceptions.RequestException as e:
								print(f"[!] Request failed: {e}")

						# Check for GameEnd event
						if(event['EventName'] == 'GameEnd'):
							try:
								gamedata_response = requests.get(LC_EVENT_URL + "/allgamedata", verify=False, timeout=2, proxies=LC_PROXIES)
								gamedata_response.raise_for_status()
								
								gamedata = gamedata_response.json()
								
								# Write to file
								try:
									file.write(str(gamedata) + '\n')
								except UnicodeEncodeError as e:
									print(f"[!] Encoding error while printing event data: {e}")
									
								# THIS IS WHERE THIS FUNCTION SHOULD HOPEFULLY END
								if CUSTOMS_SERVER_STATUS == True:
									try:
										gameend_response = requests.post(CUSTOMS_DATA_CALLBACK, json=message, headers=get_event_headers("GAME_DATA"), verify=False, timeout=2, proxies=WEB_PROXIES)
										gameend_response.raise_for_status()
									except requests.exceptions.Timeout:
										print(f"[!] Callback request timed out.")
									except requests.exceptions.RequestException as e:
										print(f"[!] Request failed: {e}")

								return
								
							except requests.exceptions.Timeout:
								print(f"[!] Gamedata request timed out.")
								time.sleep(1)
								continue
								
							except requests.exceptions.RequestException as e:
								print(f"[!] Gamedata Request failed: {e}")
								time.sleep(1)
								continue

						# iterate to next event in queue
						event_id += 1
				else:
					print(f"[!] event_data is not a list: {event_data}")
					continue

				#game_start = True
				time.sleep(1)

			except requests.exceptions.Timeout:
				print(f"[!] Request timed out. Retrying...")
				time.sleep(1)  # Optional: Wait before retrying
				continue  # Retry the request

			except requests.exceptions.RequestException as e:
				print(f"[!] Request failed: {e}")
				time.sleep(1)
				continue
	return




################### MATCH DATA ###################

# Get match IDs
def get_match_ids(puuid, count=1):
	url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
	headers = {"X-Riot-Token": RIOT_API_KEY}
	response = requests.get(url, headers=headers, proxies=WEB_PROXIES, verify=False)
	if response.status_code == 200:
		return response.json()
	else:
		print("[-] Failed to get match IDs:", response.status_code)
		return []

# Get match details
def get_match_details(match_id):
	url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
	headers = {"X-Riot-Token": RIOT_API_KEY}
	response = requests.get(url, headers=headers, proxies=WEB_PROXIES, verify=False)
	if response.status_code == 200:
		return response.json()
	else:
		print("[-] Failed to get match details:", response.status_code)
		return None


################### MAIN ###################
if __name__ == "__main__":
	# general configuration things
	requests.packages.urllib3.disable_warnings()

	# Check if uhohcustoms server is open
	CUSTOMS_SERVER_STATUS = is_port_open(CUSTOMS_HOST, CUSTOMS_PORT)
	if(CUSTOMS_SERVER_STATUS == True):
		print(f"[+] uhohcustoms is online, will report to callback!")
	else:
		print(f"[-] uhohcustoms is offline, will not report to callback")

	# main agent loop
	while True:
		# wait for game port to be open
		print(f"[?] Waiting for game port to be open")
		wait_for_port(LOCAL_HOST, LOCAL_PORT)
		print("[+] Game port open, sleeping for 3 seconds before commence")
		time.sleep(4)

		# execute game event loop
		execute_game()
		print("[+] Game concluded, sleeping 20 seconds polling again...")
		time.sleep(15)

		# pull match history
		# UNFORTUNATELY this does not work with customs game data
		#recent_match_ids = get_match_ids(SUMMONER_PUUID, count=1)
		#if recent_match_ids:
		#	match_details = get_match_details(recent_match_ids[0])
		#	if match_details:
		#		print("[+] Match details:", match_details)


