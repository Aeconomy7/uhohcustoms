import requests
import datetime
import time
import socket
import sys
import io
from config import LOCAL_HOST, LOCAL_PORT, LC_EVENT_URL, CUSTOMS_HOST, CUSTOMS_PORT, CUSTOMS_EVENT_CALLBACK, RIOT_API_KEY, SECRET_HEADER

################### GLOBALS ###################
CUSTOMS_SERVER_STATUS = False # tracks if uhohcustoms is online, True if it is, False if it isnt
LC_PROXIES = None
WEB_PROXIES = None
#LC_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }
#WEB_PROXIES = { "http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080" }

################### NETWORK STUFF ###################
def wait_for_port(host, port):
	while not is_port_open(host, port):
		#print(f"[-] Port {port} is not open. Retrying...")
		time.sleep(1)  # Wait for 2 seconds before retrying

	print(f"[+] Port {port} is now open, commence game!")
	return

def is_port_open(host, port):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.settimeout(1)  # Set a timeout for the connection attempt
		result = sock.connect_ex((host, port))
		return result == 0  # Return True if the port is open

################### LIVE CLIENT API ###################
def handle_event(event):
	event_handler = event_switch.get(event['EventName'], handle_UnknownEvent)
	return(event_handler(event))


def handle_GameStart(event):
	print("Handling Game Start event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)

def handle_ChampionKill(event):
	print("Handling Champion Kill event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_MultiKill(event):
	print("Handling Multi Kill event")
	if(event['KillStreak'] == 2):
		return f"[+] {event['EventName']} Double Kill: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)
	elif(event['KillStreak'] == 3):
		return f"[+] {event['EventName']} Triple Kill: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)
	elif(event['KillStreak'] == 4):
		return f"[+] {event['EventName']} QUADRA KILL: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)
	elif(event['KillStreak'] == 5):
		return f"[+] {event['EventName']} PENTAKILLLLLLLL: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)
	else:
		return f"[+] {event['EventName']} UNKNOWN MULTI KILL: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event) 

def handle_Ace(event):
	print("Handling Multi Kill event")
	return f"[+] {event['EventName']} ACE: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


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
	'ChampionKill': handle_ChampionKill,
	'MultiKill': handle_MultiKill,
	'Ace': handle_Ace,
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
	global CUSTOMS_SERVER_STATUS

	headers = {
		"Content-Type": "application/json",
		"X-Agent-Secret": SECRET_HEADER
	}
	event_id = 0
	file_path = f"./{str(int(time.time()))}_game.txt"
	with open(file_path, 'x', encoding='utf-8') as file:
		try:
			gamedata_response = requests.get(LC_EVENT_URL + "/allgamedata", verify=False, timeout=2, proxies=LC_PROXIES)
			gamedata_response.raise_for_status()
		except requests.exceptions.Timeout:
			print(f"[!] Gamedata request timed out.")
		except requests.exceptions.RequestException as e:
			print(f"[!] Request failed: {e}")
		while True:
			try:
				response = requests.get(LC_EVENT_URL + "/eventdata?eventID=" + str(event_id), verify=False, timeout=2, proxies=LC_PROXIES)
				response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

				event_data = response.json()

				if isinstance(event_data['Events'], list):
					for index, event in enumerate(event_data['Events']):
						message = handle_event(event)
						print(message)

						# print message to file for tracking
						try:
							file.write(message + '\n')
						except UnicodeEncodeError as e:
							print(f"[!] Encoding error while printing event data: {e}")

						if CUSTOMS_SERVER_STATUS == True:
							try:
								callback_response = requests.post(CUSTOMS_EVENT_CALLBACK, json=message, headers=headers, verify=False, timeout=2, proxies=WEB_PROXIES)
								callback_response.raise_for_status()
							except requests.exceptions.Timeout:
								print(f"[!] Callback request timed out.")
							except requests.exceptions.RequestException as e:
								print(f"[!] Request failed: {e}")

						# Check for GameEnd event
						if(event['EventName'] == 'GameEnd'):
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
		print("[+] Game concluded, sleeping 20 seconds before pulling match data...")
		time.sleep(20)

		# pull match history
		recent_match_ids = get_match_ids(SUMMONER_PUUID, count=1)
		if recent_match_ids:
			match_details = get_match_details(recent_match_ids[0])
			if match_details:
				print("[+] Match details:", match_details)


