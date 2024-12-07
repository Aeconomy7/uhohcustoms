# Library imports
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime
import json
import re

# Custom imports
from db.customsdb import CustomsDbHandler
from config import RIOT_API_KEY, FLASK_SECRET_KEY, REGION, USERS, SECRET_HEADER

#########
# FLASK #
#########
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

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
PLAYERS_DATA 		= []

ACTIVE_GAME_DATA 	= []
"""
	[
		{
			"gameID":"123e4567-e89b-12d3-a456-426614174000",
			"reporter":"Sc00by#NA1",
			"gameState":"COMPLETE"
		}
	]
"""

#####################
# UTILITY FUNCTIONS #
#####################

def app_login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'user_id' not in session:
			return redirect(url_for('login'))
		return f(*args, **kwargs)
	return decorated_function

@auth.verify_password
def verify_password(username, password):
	if username in USERS and check_password_hash(USERS[username]["password"], password):
		return username

@auth.get_user_roles
def get_user_roles(username):
	return USERS[username]["role"] if username in USERS else None

# Event handlers
def handle_event(event):
	print(f"[?] handle_event : event : {event}")
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


def handle_BaronKill(event):
	print("[+] Handling Baron Kill event")
	message = f"{event['KillerName']} felled the Baron Nashor!"
	if event['Stolen'] == 'True':
		message = message + f" HOLY SHIT WHAT A STEAL, COULD BE A GAME CHANGER!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_HeraldKill(event):
	print("[+] Handling Herald Kill event")
	message = f"{event['KillerName']} shattered the Rift Herald."
	if event['Stolen'] == 'True':
		mesage = message + f" WHAT A STEAL!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_HordeKill(event):
	print("[+] Handling Void Grubbs Kill event")
	message = f"{event['KillerName']} smashed a void grubby."
	if event['Stolen'] == 'True':
		message = message + f" WHAT A STEAL!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


#def handle_ChampionSpecialKill(event):
#	print("Handling Champion Special Kill event")
#	return f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)


def handle_EliteMonsterKill(event):
	print("[+] Handling Elite Monster Kill event")
	message = f"{event['KillerName']} has demolished the Elder Dragon!!!"
	if event['Stolen'] == 'True':
		message = message + f" HOLY SHIT WHAT A STEAL, THAT COULD BE THE GAME WINNING PLAY!"
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_GameEnd(event):
	print("Handling Game End event")
	message = f"[+] {event['EventName']}: {event['EventID']} @ {str(datetime.timedelta(seconds=round(event['EventTime'])))}: " + str(event)
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


def handle_UnknownEvent(event):
	message = f"[-] Unknown event type: {event.get('EventName', 'NoEventName')}: " + str(event)
	return event['EventID'], event['EventName'], str(datetime.timedelta(seconds=round(event['EventTime']))), message


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
	'BaronKill': handle_BaronKill,
	'HeraldKill': handle_HeraldKill,
	'HordeKill': handle_HordeKill,
#	'ChampionSpecialKill': handle_ChampionSpecialKill,
	'EliteMonsterKill': handle_EliteMonsterKill,
	'GameEnd': handle_GameEnd
}

##########
# ROUTES #
##########
@app.route('/')
@auth.login_required
def index():
	return render_template('index.html', username=session.get('username'))

# User Registration
@app.route('/register_user', methods=['GET','POST'])
@auth.login_required
def register_user():
	if request.method == 'POST':
		username = request.form['username']
		email = request.form['email']
		password = request.form['password']

		password_hash = generate_password_hash(password)

		if(CUSTOMS_DB.check_if_user_email_exists(username, email) != None):
			return jsonify({'status': 'User or email already exists'}), 400

		if(CUSTOMS_DB.register_user(username, password_hash, email)):
			return redirect(url_for('login'))
		else:
			return jsonify({'status': 'Failed to register user'}), 500

	return render_template('register_user.html', username=session.get('username'))


# Login
@app.route('/login', methods=['GET','POST'])
@auth.login_required
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']

		user = CUSTOMS_DB.get_user_by_username(username)

		if user	and check_password_hash(user[2], password):
			session['user_id'] = user[0]
			session['username'] = user[1]
			return redirect(url_for('dashboard'))
		else:
			return jsonify({'status': 'Invalid username or password'}), 403

	return render_template('login.html', username=session.get('username'))


@app.route('/logout', methods=['GET'])
def logout():
	session.clear()
	return redirect(url_for('index'))


# Dashboard
@app.route('/dashboard', methods=['GET'])
@auth.login_required
@app_login_required
def dashboard():
	if 'user_id' not in session:
		return redirect(url_for('login'))

	user_id = session['user_id']

	user = CUSTOMS_DB.get_user_by_id(user_id)
	games = []

	if user[4] != 'None':
		games = CUSTOMS_DB.get_game_history_by_team_id(user[4])

	return render_template('dashboard.html', USER_DATA=user, GAMES_DATA=games, username=session.get('username'))



# Get game events callback
@app.route('/data_callback', methods=['POST'])
def event_callback():
	global PLAYERS_DATA
	global ACTIVE_GAME_DATA

	event = request.json
	headers = request.headers
	game_id = headers.get('X-Game-ID')

	print(f"ACTIVE_GAME_DATA: {ACTIVE_GAME_DATA}")

	if isinstance(event, str):
		# Convert the string into a list of dictionaries
		event = json.loads(event)

	# Check headers and handle data accordingly
	if headers.get('X-Agent-Secret') == SECRET_HEADER:
		print(f"[?] Received callback from Game Agent: {str(event)}")
		print(f"	|-> X-Event-Type: {headers.get('X-Event-Type')}")


		# HANDLE GAME REGISTRATION
		if headers.get('X-Event-Type') == 'GAME_REGISTRATION':
			if len(ACTIVE_GAME_DATA) != 0:
				if ACTIVE_GAME_DATA[0]['game_id'] != game_id:
					return jsonify({'error': 'Active Game in Progress'}), 400
			else:
				CUSTOMS_DB.register_game(game_id)
				payload = {
					"game_id": game_id
				}
				ACTIVE_GAME_DATA.append(payload)
				print(f"[+] Successfully registered game id {game_id}! :)")

		# HANDLE PLAYER_DATA
		elif headers.get('X-Event-Type') == 'PLAYER_DATA':
			for p in event:
				print(f"p: {p}")
				PLAYERS_DATA.append(p)
				CUSTOMS_DB.register_player(p['player_name'].split('#')[0], p['player_name'].split('#')[1])
			socketio.emit('add_player_data', event)


		# HANDLE EVENT_DATA
		elif headers.get('X-Event-Type') == 'EVENT_DATA':
			event_no, event_type, game_time, message = handle_event(event)
			payload = {
				'event_id':	event_no,
				'event_type':	event_type,
				'game_time':	game_time,
				'message':	message
			}

			# push events to DB
			CUSTOMS_DB.insert_game_event(game_id, event_no, json.dumps(event))

			# OG
			socketio.emit('event_data', payload)

			# check if stats need updated
			if event['EventName'] == "ChampionKill":
				print(f"[?] Got ChampionKill event")
				assisters = set(event['Assisters'])
				for p in PLAYERS_DATA:
					pn = p['player_name'].split('#')[0]
					if pn == event['KillerName']:
						p['kills'] += 1
					elif pn == event['VictimName']:
						p['deaths'] += 1
					elif pn in assisters:
						p['assists'] += 1

				print(f"[?] PLAYERS_DATA: {PLAYERS_DATA}")
				socketio.emit('update_player_data', PLAYERS_DATA)

			# Check for GameEnd event
			if event['EventName'] == 'GameEnd':
				print(f"[?] Got GameEnd event")
				PLAYERS_DATA = []
				ACTIVE_GAME_DATA = []

		# HANDLE GAME_DATA
		elif headers.get('X-Event-Type') == 'GAME_DATA':
			print(f"[?] Got GAME_DATA")
			CUSTOMS_DB.update_end_game_history(game_id, json.dumps(event))

		else:
			print(f"[-] Found unknown X-Event-Type header")

		return jsonify({'status': 'THANKS FOR YOUR EVENT CONTRIBUTION AGENT'}), 200
	else:
		return jsonify({'error': 'Unauthorized'}), 403


# Watch live game updates
@app.route('/live_game', methods=['GET'])
@auth.login_required
def live_game():
	global PLAYERS_DATA
#	game_events_raw = CUSTOMS_DB.get_game_events_by_game_id(game_id)
#	game_events = []

#	if game_events_raw != None:
#		for event in game_events_raw:
#			event_no, event_type, game_time, message = handle_event(event)
#			payload = {
#				'event_id':     event_no,
#				'event_type':   event_type,
#				'game_time':    game_time,
#				'message':      message
#			}
#			game_events.append(game_events)

#	return render_template('live_game.html', game_events=game_events)
	return render_template('live_game.html', player_data=PLAYERS_DATA)


# Display game history
@app.route('/game_history', methods=['GET'])
@auth.login_required
def game_history():
	game_history = CUSTOMS_DB.get_all_game_history()

	return render_template('game_history.html', game_history=game_history)


#################
# JINJA FILTERS #
#################
@app.template_filter('sanitize')
def sanitize(value):
	return re.sub(r'\W+', '', value)


########
# MAIN #
########
if __name__ == '__main__':
	socketio.run(app, debug=True)

