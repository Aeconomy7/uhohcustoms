import requests
import datetime
import time
import socket
import sys
import io
import json
from config import LOCAL_HOST, LOCAL_PORT, LC_EVENT_URL, CUSTOMS_HOST, CUSTOMS_PORT, CUSTOMS_EVENT_CALLBACK, RIOT_API_KEY, SECRET_HEADER


################### GLOBALS ###################
CUSTOMS_SERVER_STATUS = False # tracks if uhohcustoms is online, True if it is, False if it isnt
PLAYERS_DATA = []
#LC_PROXIES = None
#WEB_PROXIES = None
LC_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }
WEB_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }


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
def handle_event(event):
	event_handler = event_switch.get(event['EventName'], handle_UnknownEvent)
	id, name, time, message = event_handler(event))
	return id, name, time, message


def handle_GameStart(event):
	print("[+] Handling Game Start event")
	message = f"The game has started! May the best team win."
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_MinionsSpawning(event):
	print("[+] Handling Minion Spawn event")
	message = f"The minions have began their relentless march, be ready!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_ChampionKill(event):
	print("[+] Handling Champion Kill event")
	if not event['Assisters']:
		message = f"{event['KillerName']} has slain {event['VictimName']}!"
	else:
		message = f"{event['KillerName']} has slain {event['VictimName']}. Assisters: "
		for assister in event['Assisters']:
			message = message + f"{assister} "
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_Multikill(event):
	print("[+] Handling Multi Kill event")
	message = f""
	if(event['KillStreak'] == 2):
		message = f"{event['KillerName']} got a Double Kill! Wow!"
	elif(event['KillStreak'] == 3):
		message = f"{event['KillerName']} got a Triple Kill! Holy Shiz!!"
	elif(event['KillStreak'] == 4):
		message = f"{event['KillerName']} got a QUADRA KILL! WHAT THE FRICK!"
	elif(event['KillStreak'] == 5):
		message = f"{event['KillerName']} GOT A PENTAKILLLLL PAPA JOHNS! I HAVE LOST MY MARBLES, THIS IS CUSTOMS HISTORY!!!!!"
	else:
		message = f"This should not happen, pls contact Al." 
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_Ace(event):
	print("[+] Handling Multi Kill event")
	if event['AcingTeam'] == "ORDER":
		message = f"{event['Acer']} of the Blue Team has scored an ACE-U!!!"
	elif event['AcingTeam'] == "CHAOS":
		message = f"{event['Acer']} of the Red Team has scored an ACE-U!!!"
	else:
		message = f"This should not happen, pls contact Al."  
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message
    
    
def handle_FirstBrick(event):
	print("[+] Handling First Turret event")
	message = f"{event['KillerName']} destroyed the first turret! BURN BABY BURN!!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message

# YOU ARE HERE
def handle_TurretKilled(event):
	print("Handling Turret Killed event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_InhibKilled(event):
	print("Handling Inhib Killed event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_DragonKill(event):
	print("Handling Dragon Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_BaronKill(event):
	print("Handling Baron Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_HeraldKill(event):
	print("Handling Herald Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_HordeKill(event):
	print("Handling Void Grubbs Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_ChampionSpecialKill(event):
	print("Handling Champion Special Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_EliteMonsterKill(event):
	print("Handling Elite Monster Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_FirstBlood(event):
	print("Handling First Blood event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_GameEnd(event):
	print("Handling Game End event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_UnknownEvent(event):
	return f"[-] Unknown event type: {event.get('EventName', 'NoEventName')}: " + str(event)


# Dictionary to map event names to handler functions
event_switch = {
	'GameStart': handle_GameStart,
	'MinionsSpawning': handle_MinionsSpawning,
	'ChampionKill': handle_ChampionKill,
	'Multikill': handle_Multikill,
	'Ace': handle_Ace,
	'FirstBrick': handle_FirstBrick,
    'TurretKilled': handle_TurretKilled,
	'InhibKilled': handle_InhibKilled,
	'DragonKill': handle_DragonKill,
	'BaronKill': handle_BaronKill,
	'HeraldKill': handle_HeraldKill,
	'HordeKill': handle_HordeKill,
	'ChampionSpecialKill': handle_ChampionSpecialKill,
	'EliteMonsterKill': handle_EliteMonsterKill,
	'FirstBlood': handle_FirstBlood,
	'GameEnd': handle_GameEnd
}


def execute_game():
	# Global variable declarations
	global CUSTOMS_SERVER_STATUS
	global PLAYERS_DATA

	event_id = 0
	file_path = f"./{str(int(time.time()))}_game.txt"
	event_header = "PLAYER_DATA"

	# Request variables
	headers = {
		"Content-Type": "application/json",
		"X-Agent-Secret": SECRET_HEADER,
		"X-Event-Type": event_header
	}
	
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
						'kills':		p['scores']['kills'],
						'deaths':		p['scores']['deaths'],
						'assists':		p['scores']['assists']
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
				#callback_response = requests.post(CUSTOMS_EVENT_CALLBACK, data=json.dumps(PLAYERS_DATA), headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
				callback_response = requests.post(CUSTOMS_EVENT_CALLBACK, json=PLAYERS_DATA, headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
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
						event_no, event_type, game_time, message = handle_event(event)
						payload = {
							'event_id': 	event_no,
							'event_type':	event_type,
							'game_time':	game_time,
							'message':		message
						}

						# print message to file for tracking
						try:
							file.write(message + '\n')
						except UnicodeEncodeError as e:
							print(f"[!] Encoding error while printing event data: {e}")

						if CUSTOMS_SERVER_STATUS == True:
							try:
								event_header = "EVENT_DATA"
								callback_response = requests.post(CUSTOMS_EVENT_CALLBACK, data=json.dumps(payload), headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
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
#								print(f"[?] Players in game and their champs:")
								
#								for player in gamedata['allPlayers']:
#									print("[?] player: " + str(player))
#									players.append(json.dumps(player))
#									player_info = "{" + player['riotId'] + ":" + player['championName'] + ",team:" + player['team'] + "}"
#									print("[?] player_info: " + player_info)
#									file.write(player_info + '\n')
#									if CUSTOMS_SERVER_STATUS == True:
#										try:
#											callback_response = requests.post(CUSTOMS_EVENT_CALLBACK, json=player_info, headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
#											callback_response.raise_for_status()
#										except requests.exceptions.Timeout:
#											print(f"[!] Callback request timed out.")
#											continue
#										except requests.exceptions.RequestException as e:
#											print(f"[!] Request failed: {e}")
#											continue

							except requests.exceptions.Timeout:
								print(f"[!] Gamedata request timed out.")
								time.sleep(1)
								continue
							except requests.exceptions.RequestException as e:
								print(f"[!] Gamedata Request failed: {e}")
								time.sleep(1)
								continue
							
							# THIS IS WHERE THIS FUNCTION SHOULD HOPEFULLY END
							if CUSTOMS_SERVER_STATUS == True:
								try:
									event_header = "GAME_DATA"
									gameend_response = requests.post(CUSTOMS_EVENT_CALLBACK, json=message, headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
									gameend_response.raise_for_status()
								except requests.exceptions.Timeout:
									print(f"[!] Callback request timed out.")
								except requests.exceptions.RequestException as e:
									print(f"[!] Request failed: {e}")
							return
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


