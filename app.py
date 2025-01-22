###########
# LIBRARY #
###########
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import psutil
import uuid
import requests
import datetime
import json
import re
import os
import random
import logging
from logging.handlers import RotatingFileHandler

##################
# CUSTOM IMPORTS #
##################
from db.customsdb import CustomsDbHandler
from agents.datadragon_agent import DataDragonAgent
from agents.riot_agent import RiotAgent
from config import *

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

####################
# DATADRAGON AGENT #
####################
DD_AGENT = DataDragonAgent()
DD_AGENT.__enter__()

##############
# RIOT AGENT #
##############
RIOT_AGENT = RiotAgent(RIOT_API_KEY)
RIOT_AGENT.__enter__()

###########
# LOGGING #
###########
if not os.path.exists('logs'):
	os.makedirs('logs')
log_handler = RotatingFileHandler('./logs/app.log', maxBytes=500000, backupCount=1)
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(log_formatter)

app.logger.addHandler(log_handler)
app.logger.setLevel(logging.DEBUG)

###########
# GLOBALS #
###########
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
		if 'user_uuid' not in session:
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
	app.logger.debug(f"[?] handle_event : event : {event}")
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
def index():
	return render_template('index.html')


@app.route('/riot.txt')
def riot_app_verification():
	return send_from_directory('static', 'riot.txt')



# ACTION: User Registration
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


# AUTH: RSO Login
@app.route('/login_rso')
def login_rso():
	riot_auth_url = f"{RIOT_AUTH_URL}?response_type=code&client_id={RIOT_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid"
	return redirect(riot_auth_url)


# AUTH: Login
@app.route('/login', methods=['GET','POST'])
@auth.login_required
def login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']

		user = CUSTOMS_DB.get_user_by_email(email)

		if user	and check_password_hash(user[4], password):
			session['user_uuid'] 	= user[3]
			session['username'] 	= user[1]

			user_teams = CUSTOMS_DB.get_teams_for_user(session['user_uuid'])

			session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
			session['active_team_uuid'] = str(user_teams[0][0]) if user_teams else 'None'
			session['active_team_name'] = str(user_teams[0][1]) if user_teams else 'None'
			session['role'] = 'admin' if user[1] in ADMINS else 'user'

			if DEBUG:
				app.logger.debug(f"[?][APP][login][{session['username']}] user_teams: {str(session['user_teams'])}")
				app.logger.debug(f"[?][APP][login][{session['username']}] active_team_uuid: {str(session['active_team_uuid'])}")

			return redirect(request.args.get('next', url_for('teams', team_uuid=session['active_team_uuid'])))
		else:
			flash('Invalid email or password.', 'danger')

	return render_template('login.html')


# AUTH: Logout
@app.route('/logout', methods=['GET'])
def logout():
	session.clear()
	return redirect(url_for('login'))


# AUTH: RSO Callback
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
		return redirect(url_for('dashboard', team_uuid=str(session['active_team_uuid'])))
	else:
		return f"[!][APP][callback] Error fetching token: {token_response.text}", 400


# STATIC: Teams
@app.route('/teams/<team_uuid>', methods=['GET', 'POST'])
@auth.login_required
@app_login_required
def teams(team_uuid):
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))
		
		if team_uuid == 'None':
			return redirect(url_for('manage_teams'))

		user_uuid = session['user_uuid']
		user_teams = CUSTOMS_DB.get_teams_for_user(user_uuid)
		active_team = next((team for team in user_teams if team[0] == str(team_uuid)), None)
		team_members = CUSTOMS_DB.get_team_members(active_team[0])

		if DEBUG:
			app.logger.debug(f"[?][APP][teams][{session.get('username')}] user_teams:	{user_teams}")
			app.logger.debug(f"[?][APP][teams][{session.get('username')}] active_team:	{active_team}")
			app.logger.debug(f"[?][APP][teams][{session.get('username')}] team_members:	{team_members}")

		if not active_team:
			raise ValueError('You are not currently a part of that team.')

		session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
		session['active_team_name'] = active_team[1]
		session['active_team_uuid'] = active_team[0]

	except ValueError as e:
		flash(str(e), 'danger')

	except Exception as e:
		flash('An unexpected error occurred setting active team. Please try again.', 'danger')

	return render_template('teams.html', team_members=team_members, team_name=session['active_team_name'], active_team=active_team)


# STATIC: Manage teams
@app.route('/manage_teams', methods=['GET'])
@auth.login_required
@app_login_required
def manage_teams():
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		user_uuid = session['user_uuid']
		user_teams = CUSTOMS_DB.get_teams_for_user(user_uuid)
		captain_team = None
		for team in user_teams:
			if CUSTOMS_DB.is_user_captain_of_team(user_uuid, str(team[0])) == 'Captain':
				captain_team = team
				break

		if DEBUG:
			app.logger.debug(f"[?][APP][manage_teams][{session.get('username')}] user_teams: {user_teams}")

	except Exception as e:
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('manage_teams.html', user_teams=user_teams, captain_team=captain_team)


# ACTION: Create team
@app.route('/create_team', methods=['POST'])
@auth.login_required
@app_login_required
def create_team():
	team_name = request.form['team_name']

	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		if not team_name:
			raise ValueError("Team name cannot be empty.")

		if DEBUG:
			app.logger.debug(f"[?][create_team][{session['username']}] Attempting to create team {team_name}...")

		# check if already a team captain
		if CUSTOMS_DB.is_user_captain(session['user_uuid']):
			raise ValueError("You are already the captain of a team.")

		if CUSTOMS_DB.check_if_team_exists_by_team_name(team_name) != None:
			raise ValueError("Team name already exists.")

		team_uuid = uuid.uuid4()

		if not CUSTOMS_DB.register_team(team_name, team_uuid, session['user_uuid']):
			raise ValueError("Failed to create team.")

		if not CUSTOMS_DB.join_user_to_team(session['user_uuid'], team_uuid):
			raise ValueError("Failed to join team.")

		session['user_teams'].append({'team_name': team_name, 'team_uuid': team_uuid})
		session['active_team_uuid'] = team_uuid
		session['active_team_name'] = team_name

		if DEBUG:
			app.logger.debug(f"[+][create_team][{session['username']}] Successfully created team {team_name}:{session['active_team_uuid']}")
		flash(f"Successfully created {team_name}, you are the captain now!", 'success')

	except ValueError as e:
		flash(str(e), 'danger')

	except Exception as e:
		flash('An unexpected error occurred creating the team. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('teams', team_uuid=session['active_team_uuid'])))


# ACTION: Join team
@app.route('/join_team/<team_uuid>', methods=['GET', 'POST'])
@auth.login_required
@app_login_required
def join_team(team_uuid='None'):
	if 'user_uuid' not in session:
		return redirect(url_for('login'), next=request.path)
	
	# check if its POST or GET request
	if request.method == 'POST':
		team_uuid = request.form['team_uuid']

	try:
		if not team_uuid:
			raise ValueError("Team code cannot be empty.")

		if DEBUG:
			app.logger.debug(f"[?][APP][join_team][{session['username']}] Attempting to join team {team_uuid}...")

		# Check if team exists by uuid and if they are already a team member
		teamcheck = CUSTOMS_DB.check_if_team_exists_by_team_uuid(team_uuid)
		if teamcheck == None:
			raise ValueError("Team code is invalid.")

		userteamcheck = CUSTOMS_DB.get_teams_for_user(session['user_uuid'])
		for team in userteamcheck:
			if team[0] == str(team_uuid):
				raise ValueError("You are already a member of this team.")

		# perform the team join
		if not CUSTOMS_DB.join_user_to_team(session['user_uuid'], team_uuid):
			raise ValueError("Failed to join team.")

		# LOOK HERE FOR ERRORS WITH JOIN_TEAM IN THE FUTURE MAYBE
		session['user_teams'].append({'team_name': teamcheck[1], 'team_uuid': team_uuid})
		session['active_team_uuid'] = team_uuid
		session['active_team_name'] = teamcheck[1]

		if DEBUG:
			app.logger.debug(f"[+][APP][join_team][{session['username']}] Successfully joined team {teamcheck[1]}:{team_uuid}")
		flash(f"You have successfully joined {teamcheck[1]}!", 'success')

	except ValueError as e:
		flash(str(e), 'danger')

	except Exception as e:
		flash('An unexpected error occurred joining a team. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('teams', team_uuid=session.get('active_team_uuid'))))


# ACTION: Leave Team
@app.route('/leave_team/<team_uuid>', methods=['GET', 'POST'])
@auth.login_required
@app_login_required
def leave_team(team_uuid):
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	# check if its POST or GET request
	if request.method == 'POST':
		team_uuid = request.form['team_uuid']

	try:

		if team_uuid == 'None':
			raise ValueError("Invalid team to leave")

		if DEBUG:
			app.logger.debug(f"[?][APP][leave_team][{session['username']}] Attempting to leave team {team_uuid}...")

		# check if user is team captain and disallow if so
		if CUSTOMS_DB.is_user_captain_of_team(session.get('user_uuid'), team_uuid):
			raise ValueError("Cannot abandon team as the captain of the ship!")

		if not CUSTOMS_DB.remove_user_from_team(session['user_uuid'], team_uuid):
			raise ValueError("Failed to leave team.")

		user_teams = CUSTOMS_DB.get_teams_for_user(session['user_uuid'])
		session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
		session['active_team_uuid'] = str(user_teams[0][0]) if user_teams else 'None'
		session['active_team_name'] = str(user_teams[0][1]) if user_teams else 'None'

		if DEBUG:
			app.logger.debug(f"[+][APP][leave_team][{session['username']}] Successfully left team {team_uuid}")
		flash(f"You have successfully left the team.", 'success')

	except ValueError as e:
		flash(str(e), 'danger')

	except Exception as e:
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('teams', team_uuid=session.get('active_team_uuid'))))




# New Game Upload - manual and file upload
@app.route('/add_game', methods=['GET', 'POST'])
@auth.login_required
@app_login_required
def add_game():
	return render_template('add_game.html')


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
		app.logger.debug(f"[?] Received callback from Game Agent: {str(event)}")
		app.logger.debug(f"	|-> X-Event-Type: {headers.get('X-Event-Type')}")


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
				app.logger.debug(f"[+] Successfully registered game id {game_id}! :)")

		# HANDLE PLAYER_DATA
		elif headers.get('X-Event-Type') == 'PLAYER_DATA':
			for p in event:
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
				app.logger.debug(f"[?] Got ChampionKill event")
				assisters = set(event['Assisters'])
				for p in PLAYERS_DATA:
					pn = p['player_name'].split('#')[0]
					if pn == event['KillerName']:
						p['kills'] += 1
					elif pn == event['VictimName']:
						p['deaths'] += 1
					elif pn in assisters:
						p['assists'] += 1

				app.logger.debug(f"[?] PLAYERS_DATA: {PLAYERS_DATA}")
				socketio.emit('update_player_data', PLAYERS_DATA)

			# Check for GameEnd event
			if event['EventName'] == 'GameEnd':
				app.logger.debug(f"[?] Got GameEnd event")
				PLAYERS_DATA = []
				ACTIVE_GAME_DATA = []

		# HANDLE GAME_DATA
		elif headers.get('X-Event-Type') == 'GAME_DATA':
			app.logger.debug(f"[?] Got GAME_DATA")
			CUSTOMS_DB.update_end_game_history(game_id, json.dumps(event))

		else:
			app.logger.debug(f"[-] Found unknown X-Event-Type header")

		return jsonify({'status': 'THANKS FOR YOUR EVENT CONTRIBUTION AGENT'}), 200
	else:
		return jsonify({'error': 'Unauthorized'}), 403


# Watch live game updates
@app.route('/live_game', methods=['GET'])
@auth.login_required
def live_game():
	global PLAYERS_DATA

	return render_template('live_game.html', player_data=PLAYERS_DATA)


# ADMIN ROUTES
@app.route('/uhohadmin')
@auth.login_required
@app_login_required
def uhohadmin():
	# DOUBLE CHECK FOR FUNKINESS
	if session.get('username') not in ADMINS:
		return redirect(url_for('uhoh', error_code=403))
	
	if DEBUG:
		app.logger.debug(f"[?][APP][uhohadmin][{session.get('username')}] Admin access granted.")

	# app stats
	total_users = CUSTOMS_DB.get_total_users()
	total_teams = CUSTOMS_DB.get_total_teams()
	total_games = CUSTOMS_DB.get_total_games()

	# server stats
	uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
	memory = psutil.virtual_memory()
	cpu = psutil.cpu_percent(interval=1)

	# image data
	champions = DD_AGENT.get_images_by_category('champion')
	items = DD_AGENT.get_images_by_category('item')
	spells = DD_AGENT.get_images_by_category('spell')
	runes = DD_AGENT.get_images_by_category('runes')

	return render_template('uhohadmin.html', total_users=total_users, total_teams=total_teams, total_games=total_games, uptime=uptime, memory=memory, cpu=cpu, current_patch=DD_AGENT.get_current_patch(), champions=champions, items=items, spells=spells, runes=runes)

# ERROR ROUTES
@app.route('/uhoh/<int:error_code>')
@auth.login_required
@app_login_required
def uhoh(error_code):
	error_image_folder = os.path.join(app.static_folder, 'img', 'error')
	error_images = os.listdir(error_image_folder)
	random_image = random.choice(error_images)
	
	return render_template('uhoh.html', error_code=error_code, error_image=random_image)

@app.errorhandler(400)
def bad_request(e):
	return redirect(url_for('uhoh', error_code=400))

@app.errorhandler(401)
def unauthorized(e):
	return redirect(url_for('uhoh', error_code=401))

@app.errorhandler(403)
def forbidden(e):
	return redirect(url_for('uhoh', error_code=403))

@app.errorhandler(404)
def page_not_found(e):
	return redirect(url_for('uhoh', error_code=404))

@app.errorhandler(500)
def internal_server_error(e):
	return redirect(url_for('uhoh', error_code=500))


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
	app.logger.debug(f"[?] APP DEBUG MODE: {DEBUG}")
	socketio.run(app, debug=DEBUG)

