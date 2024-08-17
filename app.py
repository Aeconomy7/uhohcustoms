# Library imports
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash
import requests
import datetime

# Custom imports
from db.customsdb import CustomsDbHandler
from config import RIOT_API_KEY, FLASK_SECRET_KEY, REGION, USERS, SECRET_HEADER

#########
# FLASK #
#########
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY  # Change this to a secure key

auth = HTTPBasicAuth()

socketio = SocketIO(app)

######
# DB #
######
CUSTOMS_DB = CustomsDbHandler()
CUSTOMS_DB.__enter__()

###########
# GLOBALS #
###########
PLAYERS_DATA = []

#####################
# UTILITY FUNCTIONS #
#####################
@auth.verify_password
def verify_password(username, password):
	if username in USERS and check_password_hash(USERS[username]["password"], password):
		return username

@auth.get_user_roles
def get_user_roles(username):
	return USERS[username]["role"] if username in USERS else None

# Event handlers
def handle_event(event):
	event_handler = event_switch.get(event['EventName'], handle_UnknownEvent)
	id, name, time, message = event_handler(event)
	return id, name, time, message


def handle_GameStart(event):
	print("[+] Handling Game Start event")
	message = f"The game has started! May the best team win."
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_MinionsSpawning(event):
	print("[+] Handling Minion Spawn event")
	message = f"The minions have begun their relentless march, be ready!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_FirstBlood(event):
	print("[+] Handling First Blood event")
	message = f"{event['Recipient']} got first blood! BOOYAH!!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_ChampionKill(event):
	print("[+] Handling Champion Kill event")
	message = f""
	if not event['Assisters']:
		message = f"{event['KillerName']} has slain {event['VictimName']}!"
	else:
		message = f"{event['KillerName']} has slain {event['VictimName']}. Assisted By: "
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
	message = f""
	if event['AcingTeam'] == "ORDER":
		message = f"{event['Acer']} of the Blue Team has scored an ACE-U!!!"
	elif event['AcingTeam'] == "CHAOS":
		message = f"{event['Acer']} of the Red Team has scored an ACE-U!!!"
	else:
		message = f"This should not happen, pls contact Al."
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_FirstBrick(event):
	print("[+] Handling First Turret event")
	message = f"{event['KillerName']} destroyed the first tower! BURN BABY BURN!!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_TurretKilled(event):
	print("[+] Handling Turret Killed event")
	message = f"{event['KillerName']} destroyed a tower. Anotha one bites the dust!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_InhibKilled(event):
	print("[+] Handling Inhib Killed event")
	message = f"{event['KillerName']} destroyed an inhibitor. Super minions incoming!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_DragonKill(event):
	print("[+] Handling Dragon Kill event")
	message = f"{event['KillerName']} has slain the {event['DragonType']} Dragon!"
	if event['Stolen'] == 'True':
		message = message + f" WHAT A STEAL!!!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message

"""
def handle_BaronKill(event):
	print("[+] Handling Baron Kill event")
	message = f""
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


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
"""

def handle_GameEnd(event):
	print("Handling Game End event")
	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_UnknownEvent(event):
	return f"[-] Unknown event type: {event.get('EventName', 'NoEventName')}: " + str(event)


# Dictionary to map event names to handler functions
event_switch = {
	'GameStart': handle_GameStart,
	'MinionsSpawning': handle_MinionsSpawning,
	'FirstBlood': handle_FirstBlood,
	'ChampionKill': handle_ChampionKill,
	'Multikill': handle_Multikill,
	'Ace': handle_Ace,
	'FirstBrick': handle_FirstBrick,
	'TurretKilled': handle_TurretKilled,
	'InhibKilled': handle_InhibKilled,
	'DragonKill': handle_DragonKill,
#	'BaronKill': handle_BaronKill,
#	'HeraldKill': handle_HeraldKill,
#	'HordeKill': handle_HordeKill,
#	'ChampionSpecialKill': handle_ChampionSpecialKill,
#	'EliteMonsterKill': handle_EliteMonsterKill,
	'GameEnd': handle_GameEnd
}

##########
# ROUTES #
##########
@app.route('/')
@auth.login_required
def index():
	global active_match_id

	print(f"[!] Enter INDEX, active_match_id: {active_match_id}")

	return render_template('index.html', active_match_id=active_match_id)


# Get game events callback
@app.route('/data_callback', methods=['POST'])
def event_callback():
	global PLAYERS_DATA

	event = request.json
	headers = request.headers

	if isinstance(event, str):
		# Convert the string into a list of dictionaries
		event = json.loads(event)

	# Check headers and handle data accordingly
	if headers.get('X-Agent-Secret') == SECRET_HEADER:
		print(f"[?] Received callback from Game Agent: {str(event)}")
		print(f"	|-> X-Event-Type: {headers.get('X-Event-Type')}")


		# HANDLE PLAYER_DATA
		if headers.get('X-Event-Type') == 'PLAYER_DATA':
			for p in event:
				print(f"p: {p}")
				PLAYERS_DATA.append(p)
			socketio.emit('add_player_data', event)

		# HANDLE EVENT_DATA
		elif headers.get('X-Event-Type') == 'EVENT_DATA':
			# BEGIN PASTED CODE
			event_no, event_type, game_time, message = handle_event(event)
			payload = {
				'event_id':	event_no,
				'event_type':	event_type,
				'game_time':	game_time,
				'message':	message
			}

			# OG
			socketio.emit('event_data', payload)

			# check if stats need updated
			if event['EventName'] == "ChampionKill":
				print(f"[?] Got ChampionKill event")
				assisters = set(event['Assisters'])
				for p in PLAYERS_DATA:
					pn = p['player_name'].split('#')[0]
					if pn == event['KillerName']:
						p["kills"] += 1
					if pn == event['VictimName']:
						p["deaths"] += 1
					if pn in assisters:
						p["assists"] += 1

				print(PLAYERS_DATA)
				socketio.emit('update_player_data', PLAYERS_DATA)

			# Check for GameEnd event
			if event['EventName'] == 'GameEnd':
				print(f"[?] Got GameEnd event")
				PLAYERS_DATA = []


		# HANDLE GAME_DATA
		elif headers.get('X-Event-Type') == 'GAME_DATA':
			print(f"[*] Got GAME_DATA, no yet implemented")

		else:
			print(f"[-] Found unknown X-Event-Type header")

		return jsonify({'status': 'THANKS FOR YOUR EVENT CONTRIBUTION AGENT'}), 200
	else:
		return jsonify({'error': 'Unauthorized'}), 403


# Watch live game updates
@app.route('/live_game', methods=['GET'])
@auth.login_required
def live_game():
	return render_template('live_game.html')


@app.route('/customs_history', methods=['GET'])
@auth.login_required
def customs_history():
	global active_tournament_id

	match_history = CUSTOMS_DB.get_match_history()

	return render_template('match_history.html', tournament_id=active_tournament_id, match_history=match_history)

########
# MAIN #
########
if __name__ == '__main__':
	socketio.run(app, debug=True)

