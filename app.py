###########
# LIBRARY #
###########
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import requests
import datetime
import json
import re

##################
# CUSTOM IMPORTS #
##################
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
# Riot API configuration
RIOT_CLIENT_ID		= "your_client_id"
RIOT_CLIENT_SECRET	= "your_client_secret"
RIOT_AUTH_URL		= "https://auth.riotgames.com/authorize"
RIOT_TOKEN_URL		= "https://auth.riotgames.com/token"
REDIRECT_URI		= "https://uhohcustoms.lol/callback"

DEBUG			= True

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
#@auth.login_required
def index():
	return render_template('index.html', username=session.get('username'))


@app.route('/riot.txt')
def riot_app_verification():
	return send_from_directory('static', 'riot.txt')



# User Registration
@app.route('/register_user', methods=['GET','POST'])
@auth.login_required
def register_user():
	if request.method == 'POST':
		valid = True

		username = request.form['username']
		if not username.isalnum() or len(username) > 16:
			flash('Username must be alphanumeric and no longer than 16 characters.', 'danger')
			valid = False

		email = request.form['email']
		if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
			flash('Email is not in a valid format.', 'danger')
			valid = False

		password = request.form['password']
		if not password or len(password) < 10:
			flash('Password must be at least 10 characters long.', 'danger')
			valid = False

		if password != request.form['confirm_password']:
			flash('Passwords do not match.', 'danger')
			valid = False

		if not valid:
			return redirect(url_for('register_user'))

		password_hash = generate_password_hash(password)
		user_uuid = uuid.uuid4()

		if(CUSTOMS_DB.check_if_user_email_exists(username, email) != None):
			flash('User or email already exists.', 'danger')
			return redirect(url_for('register_user'))

		if(CUSTOMS_DB.register_user(username, user_uuid, email, password_hash)):
			flash('Successfully registered user!', 'success')
			return redirect(url_for('login'))
		else:
			flash('Failed to register user.', 'danger')

	return render_template('register_user.html')


# RSO Login
@app.route('/login_rso')
def login_rso():
	riot_auth_url = f"{RIOT_AUTH_URL}?response_type=code&client_id={RIOT_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid"
	return redirect(riot_auth_url)


# Login
@app.route('/login', methods=['GET','POST'])
@auth.login_required
def login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']

		user = CUSTOMS_DB.get_user_by_email(email)

		if user	and check_password_hash(user[4], password):
			session['user_id'] 	= user[3]
			session['username'] 	= user[1]
			session['email'] 	= user[2]
			session['team']		= user[5]
			session['status']	= user[6]
			return redirect(url_for('dashboard'))
		else:
			flash('Invalid email or password.', 'danger')

	return render_template('login.html')


# Logout
@app.route('/logout', methods=['GET'])
def logout():
	session.clear()
	return redirect(url_for('login'))


# RSO Callback
@app.route('/callback')
def callback():
	code = request.args.get('code')

	token_response = requests.post(
		RIOT_TOKEN_URL,
		data = {
			"grant_type": "authorization_code",
			"code": code,
			"redirect_url": REDIRECT_URI,
			"client_id": RIOT_CLIENT_ID,
			"client_secret": RIOT_CLIENT_SECRET
		}
	)

	if token_response.status_code == 200:
		token_data = token_response.json()
		session['access_token'] = token_data['access_token']
		return redirect(url_for('dashboard'))
	else:
		return f"Error fetching token: {token_response.text}", 400

# Create team
@app.route('/create_team', methods=['POST'])
@auth.login_required
@app_login_required
def create_team():
	team_name = request.form['team_name']

	try:
		if 'username' not in session:
			raise ValueError("Invalid session.")

		if not team_name:
			raise ValueError("Team name cannot be empty.")

		if session['team'] != 'None':
			raise ValueError("You cannot create a team if you have already joined a team.")

		if CUSTOMS_DB.check_if_team_exists_by_team_name(team_name) != None:
			raise ValueError("Team name already exists.")

		team_uuid = uuid.uuid4()

		if not CUSTOMS_DB.register_team(team_name, team_uuid):
			raise ValueError("Failed to create team.")

		if not CUSTOMS_DB.join_user_to_team(session['username'], 'Owner', team_uuid):
			raise ValueError("Failed to join team.")

		session['team'] = team_uuid
		session['status'] = 'Owner'
		flash("Successfully created and joined team!", 'success')

	except ValueError as e:
		flash(str(e), 'danger')

	except Exception as e:
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(url_for('dashboard'))


# Approve team member


# Join team
@app.route('/join_team', methods=['POST'])
@auth.login_required
@app_login_required
def join_team():
	team_uuid = request.form['team_code']

	try:
		if 'username' not in session:
			raise ValueError("Invalid session.")

		if session['team'] != 'None':
			raise ValueError("Already joined a team.")

		username = session['username']

		if not team_uuid:
			raise ValueError("Team code cannot be empty.")

		team = CUSTOMS_DB.check_if_team_exists_by_team_uuid(team_uuid)

		if team == None:
			raise ValueError("Team code is invalid.")

		if not CUSTOMS_DB.join_user_to_team(username, 'Pending', team_uuid):
			raise ValueError("Failed to join team.")

		session['team'] = team_uuid
		flash(f"You are pending joining {team[1]}!", 'success')

		#return jsonify({'status': 'Successfully joined team'}), 200

	except ValueError as e:
		flash(str(e), 'danger')
		#return jsonify({'status': 'Failed to join team'}), 400

	except Exception as e:
		flash('An unexpected error occurred. Please try again.', 'danger')
		#return jsonify({'status': 'Unexpected error'}), 500

	return redirect(url_for('dashboard'))


# Leave Team
@app.route('/leave_team', methods=['POST'])
@auth.login_required
@app_login_required
def leave_team():
	try:
		if 'username' not in session:
			raise ValueError("Invalid session.")

		if session['team'] == 'None':
			raise ValueError("Not part of a team.")

		if not CUSTOMS_DB.join_user_to_team(session['username'], 'None', 'None'):
			raise ValueError("Failed to leave team.")

		flash(f"You have successfully left your team, time to join a new one!", 'success')
		session['team'] = 'None'

	except ValueError as e:
		flash(str(e), 'danger')
		#return jsonify({'status': 'Failed to join team'}), 400

	except Exception as e:
		flash('An unexpected error occurred. Please try again.', 'danger')
		#return jsonify({'status': 'Unexpected error'}), 500

	return redirect(url_for('dashboard'))


# New Game Upload - manual and file upload
@app.route('/new_game', methods=['GET', 'POST'])
@auth.login_required
@app_login_required
def new_game():
	return render_template('new_game.html')


# Dashboard
@app.route('/dashboard', methods=['GET'])
@auth.login_required
@app_login_required
def dashboard():
	if 'user_id' not in session:
		return redirect(url_for('login'))


	teams 	= {}
	games 	= {}
	players	= {}
	user 	= {
		'user_id': 	session['user_id'],
		'username':	session['username'],
		'email':	session['email'],
		'team':		session['team'],
		'status':	session['status']
	}


	if user['team'] != 'None':
		members = CUSTOMS_DB.get_users_by_team_uuid(user['team'])
		team_owner = ''
		if members != None:
			for mem in members:
				print(mem)
				if mem[1] == 'Owner':
					team_owner = mem[0]
		games = CUSTOMS_DB.get_game_history_by_team_uuid(user['team'])
		team_data = CUSTOMS_DB.get_team_by_team_uuid(user['team'])
		teams = {
			'members': 	members,
			'team_name': 	team_data[1],
			'team_uuid': 	user['team'],
			'team_owner':	team_owner
		}

	if DEBUG:
		print(f"[?] Rendering dashboard with the following: ")
		print(f"	|-> user:  {user}")
		print(f"	|-> teams: {teams}")
		print(f"	|-> games: {games}")

	return render_template('dashboard.html', USER_DATA=user, GAMES_DATA=games, TEAM_DATA=teams, PLAYERS_DATA=players, username=session.get('username'))


# Display game stats
#@app.route('/game/<game_id>')
#@app_login_required
#def game_history(game_id):
	# Fetch the game blob from the database
#	game_blob = CUSTOMS_DB.get_game_history_by_game_id(game_id)

#	if not game_blob:
#		flash("Game not found.", "danger")
#		return redirect(url_for('dashboard'))

#	game_data = json.loads(game_blob)

#	return render_template('game_history.html', game_data=game_data)


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
				if DEBUG:
					print(f"p: {p}")
				player_name	= p['player_name'].split('#')[0]
				player_tag	= p['player_name'].split('#')[1]
				PLAYERS_DATA.append(p)
				if CUSTOMS_DB.get_player(player_name, player_tag) is None:
					CUSTOMS_DB.register_player(player_name, player_tag)
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
#				'event_id':	 event_no,
#				'event_type':   event_type,
#				'game_time':	game_time,
#				'message':	  message
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

