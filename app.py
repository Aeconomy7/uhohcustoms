###########
# LIBRARY #
###########
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import psutil
import uuid
import requests
import datetime
import json
import re
import os
import time
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

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

########
# AUTH #
########
auth = HTTPBasicAuth()


##############
# WEBSOCKETS #
##############
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
if not os.path.exists('static/game_data'):
	os.makedirs('static/game_data')
RIOT_AGENT = RiotAgent(RIOT_API_KEY, RIOT_AUTH_URL, RIOT_TOKEN_URL, REDIRECT_URI, SERVER_REGION, MATCH_REGION)
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
DEBUG				= True
SUPPORTED_REGIONS	= ['NA1', 'EUW1', 'EUN1', 'KR', 'BR1', 'LA1', 'LA2', 'OC1', 'JP1', 'TR1', 'RU']


#####################
# UTILITY FUNCTIONS #
#####################
def sanitize_game_code(game_code):
	return re.sub(r'[^a-zA-Z0-9_]', '', game_code)

def get_match_region(game_region):
	region_mapping = {
		'NA1': 'americas',
		'BR1': 'americas',
		'LAN': 'americas',
		'LAS': 'americas',
		'OCE': 'americas',
		'EUW1': 'europe',
		'EUNE1': 'europe',
		'TR1': 'europe',
		'RU': 'europe',
		'KR': 'asia',
		'JP1': 'asia',
		'SG2': 'sea',
		'PH2': 'sea',
		'TH2': 'sea',
		'TW2': 'sea',
		'VN2': 'sea'
	}
	return region_mapping.get(game_region, 'unknown')

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



##########
# ROUTES #
##########
@app.route('/')
def index():
	return render_template('index.html')


@app.route('/about')
def about():
	return render_template('about.html')


# for riot site verification
@app.route('/riot.txt')
def riot_app_verification():
	return send_from_directory('static', 'riot.txt')


# ACTION: User Registration
@app.route('/register', methods=['GET','POST'])
@limiter.limit("5 per minute")
#@auth.login_required
def register():
	if request.method == 'POST':
		valid = True

		username = request.form['username']
		if not username.isalnum() or len(username) > 16:
			flash('Username must be alphanumeric and no longer than 16 characters.', 'danger')
			valid = False

		email = request.form['email']
		#if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
		if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
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
			return redirect(url_for('register'))

		password_hash = generate_password_hash(password)
		user_uuid = uuid.uuid4()

		if(CUSTOMS_DB.check_if_user_email_exists(username, email) != None):
			flash('User or email already exists.', 'danger')
			return redirect(url_for('register'))

		if(CUSTOMS_DB.register_user(username, user_uuid, email, password_hash)):
			flash('Successfully registered user!', 'success')
			return redirect(url_for('login'))
		else:
			flash('Failed to register user.', 'danger')

	return render_template('register.html')


# AUTH: RSO Login
@app.route('/login_rso')
def login_rso():
	riot_auth_url = f"{RIOT_AUTH_URL}?response_type=code&client_id={RIOT_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid"
	return redirect(riot_auth_url)


# AUTH: Login
@app.route('/login', methods=['GET','POST'])
@limiter.limit("5 per minute")
#@auth.login_required
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

			return redirect(request.args.get('next', url_for('game_history')))
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


# STATIC: Set active team
@app.route('/set_active_team/<team_uuid>', methods=['GET', 'POST'])
#@auth.login_required
@app_login_required
def set_active_team(team_uuid):
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))
		
		if team_uuid == 'None':
			return redirect(url_for('manage_teams'))

		user_uuid = session['user_uuid']
		user_teams = CUSTOMS_DB.get_teams_for_user(user_uuid)
		active_team = next((team for team in user_teams if team[0] == str(team_uuid)), None)
		#team_members = CUSTOMS_DB.get_team_members(active_team[0])

		if DEBUG:
			app.logger.debug(f"[?][APP][set_active_team][{session.get('username')}] user_teams:	{user_teams}")
			app.logger.debug(f"[?][APP][set_active_team][{session.get('username')}] active_team:	{active_team}")

		if not active_team:
			raise ValueError('You are not currently a part of that team.')

		session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
		session['active_team_name'] = active_team[1]
		session['active_team_uuid'] = active_team[0]

	except ValueError as e:
		app.logger.error(f"[!][APP][set_active_team][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][set_active_team][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred setting active team. Please try again.', 'danger')

	return redirect(url_for('game_history'))
	#return redirect(url_for('teams', team_uuid=session['active_team_uuid']))


# # STATIC: Teams
# @app.route('/teams/<team_uuid>', methods=['GET', 'POST'])
# #@auth.login_required
# @app_login_required
# def teams(team_uuid):
# 	try:
# 		if 'user_uuid' not in session:
# 			return redirect(url_for('uhoh', error_code=401))
		
# 		if team_uuid == 'None':
# 			return redirect(url_for('manage_teams'))

# 		user_uuid = session['user_uuid']
# 		user_teams = CUSTOMS_DB.get_teams_for_user(user_uuid)
# 		active_team = next((team for team in user_teams if team[0] == str(team_uuid)), None)
# 		team_members = CUSTOMS_DB.get_team_members(active_team[0])

# 		if DEBUG:
# 			app.logger.debug(f"[?][APP][teams][{session.get('username')}] user_teams:	{user_teams}")
# 			app.logger.debug(f"[?][APP][teams][{session.get('username')}] active_team:	{active_team}")
# 			app.logger.debug(f"[?][APP][teams][{session.get('username')}] team_members:	{team_members}")

# 		if not active_team:
# 			raise ValueError('You are not currently a part of that team.')

# 		session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
# 		session['active_team_name'] = active_team[1]
# 		session['active_team_uuid'] = active_team[0]

# 		team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
# 		games_info = []
# 		for game in team_game_data:
# 			game_code = game[0]

# 			# game blob data
# 			game_info = json.loads(game[1])['info']
			
# 			# date played
# 			date_played_timestamp = game_info['gameCreation'] / 1000  # Convert milliseconds to seconds
# 			date_played = datetime.datetime.fromtimestamp(date_played_timestamp).strftime('%Y-%m-%d %H:%M:%S')

# 			# player data
# 			players_data = game_info['participants']
# 			blue_team_players = [
# 				{
# 					'summoner_name': f"{player['riotIdGameName']}#{player['riotIdTagline']}",
# 					'champion_name': player['championName']
# 				}
# 				for player in players_data if player['teamId'] == 100
# 			]
# 			red_team_players = [
# 				{
# 					'summoner_name': f"{player['riotIdGameName']}#{player['riotIdTagline']}",
# 					'champion_name': player['championName']
# 				}
# 				for player in players_data if player['teamId'] == 200
# 			]

# 			# team data
# 			teams = game_info['teams']
# 			blue_team = next(team for team in teams if team['teamId'] == 100)
# 			game_result = "Blue" if blue_team['win'] else "Red"
			
# 			games_info.append({
# 				'game_code': game_code,
# 				'blue_team_players': blue_team_players,
# 				'red_team_players': red_team_players,
# 				'date_played': date_played,
# 				'game_result': game_result
# 			})

# 		return render_template('teams.html', 
# 						games_info=games_info, 
# 						team_members=team_members, 
# 						team_name=session['active_team_name'], 
# 						active_team=active_team)
		
# 	except ValueError as e:
# 		flash(str(e), 'danger')

# 	except Exception as e:
# 		flash('An unexpected error occurred setting active team. Please try again.', 'danger')

# 	return render_template('teams.html', 
# 						games_info=None, 
# 						team_members=team_members, 
# 						team_name=session['active_team_name'], 
# 						active_team=active_team)


# STATIC: Manage teams
@app.route('/manage_teams', methods=['GET'])
#@auth.login_required
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
		app.logger.error(f"[!][APP][manage_teams][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('manage_teams.html', user_teams=user_teams, captain_team=captain_team)


# ACTION: Create team
@app.route('/create_team', methods=['POST'])
#@auth.login_required
@app_login_required
def create_team():
	team_name = request.form['team_name']

	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		if not team_name:
			raise ValueError("Team name cannot be empty.")

		if not re.match(r"^[a-zA-Z0-9_]*$", team_name) or len(team_name) > 20:
			raise ValueError("Team name must be alphanumeric and <= 20 characters.")

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
		app.logger.error(f"[!][APP][create_team][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][create_team][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred creating the team. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('game_history')))
	#return redirect(request.args.get('next', url_for('teams', team_uuid=session['active_team_uuid'])))


# ACTION: Join team
@app.route('/join_team/<team_uuid>', methods=['GET', 'POST'])
#@auth.login_required
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
		app.logger.error(f"[!][APP][join_team][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][join_team][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred joining a team. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('game_history')))
	#return redirect(request.args.get('next', url_for('teams', team_uuid=session.get('active_team_uuid'))))


# ACTION: Leave Team
@app.route('/leave_team/<team_uuid>', methods=['GET', 'POST'])
#@auth.login_required
@app_login_required
def leave_team(team_uuid):
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	# check if its POST or GET request
	#if request.method == 'POST':
	#	team_uuid = request.form['team_uuid']

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
		app.logger.error(f"[!][APP][leave_team][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][leave_team][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(request.args.get('next', url_for('game_history')))
	#return redirect(request.args.get('next', url_for('teams', team_uuid=session.get('active_team_uuid'))))





# New Game Upload - manual and file upload
@app.route('/add_game', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
#@auth.login_required
@app_login_required
def add_game():
	if request.method == 'GET':
		return render_template('add_game.html')

	try:
		if request.method == 'POST':
			checker = True
			
			# check that region and game_num_id are both valid and only then pass to riot API
			# do all the sanitization
			game_region = request.form['region']
			if game_region not in SUPPORTED_REGIONS:
				raise ValueError("Invalid region.")
			
			game_num_id = request.form['game_code']
			if game_num_id.isnumeric() == False or len(game_num_id) < 10 or len(game_num_id) > 32:
				raise ValueError("Invalid game code format.")
			
			game_code = f"{game_region}_{game_num_id}"

			if not re.match(r"^(NA1|EUW1|EUNE1|KR|BR1|JP1|LAN|LAS|OCE|TR1|RU)_\d{1,32}$", game_code):
				raise ValueError("Invalid game code format. It should be in the format REGION_<some number between 1 and 32 digits>.", 'danger')

			# check if game already exists for current team
			if CUSTOMS_DB.check_if_team_game_exists(game_code, session['active_team_uuid']):
				raise ValueError(f"Game {game_code} already exists for current team.")

			file_path = os.path.join("static", "game_data", sanitize_game_code(game_code) + ".json")
			game_data = None

			# check if json file already exists
			if os.path.exists(file_path):
				with open (file_path, 'r') as f:
					game_data = json.load(f)
					checker = False

			# if not, attempt to fetch from riot api
			if game_data == None:	
				game_data = RIOT_AGENT.fetch_match_data(game_code, get_match_region(game_region))
				if game_data:
					flash(f"Game {game_code} successfully added!", 'success')
					with open(file_path, 'w') as f:
						json.dump(game_data, f)

			# check if file and riot API failed
			if game_data == None:
				raise ValueError(f"Failed to fetch game data for game ID {game_code}.")
			
			# add game blob to table if it does not exist
			if checker:
				if not CUSTOMS_DB.add_game(game_code, json.dumps(game_data)):
					raise ValueError("Failed to add game data to database.")
				
			# add game id to team_game table
			if not CUSTOMS_DB.add_team_game(session.get('active_team_uuid'), game_code):
				raise ValueError("Failed to add game data to team.")

			return redirect(url_for('game_history.html'))
		
	except ValueError as e:
		app.logger.error(f"[!][APP][add_game][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][add_game][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('add_game.html')


# ACTION: See all games history for a team
@app.route('/game_history', methods=['GET'])
#@auth.login_required
@app_login_required
def game_history():
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	try:
		team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		games_info = []
		for game in team_game_data:
			game_code = game[0]

			# game blob data
			game_info = json.loads(game[1])['info']
			
			# date played
			date_played_timestamp = game_info['gameCreation'] / 1000  # Convert milliseconds to seconds
			date_played = datetime.datetime.fromtimestamp(date_played_timestamp).strftime('%Y-%m-%d %H:%M:%S')

			# player data
			players_data = game_info['participants']
			blue_team_players = [
				{
					'summoner_name': f"{player['riotIdGameName']}#{player['riotIdTagline']}",
					'champion_name': player['championName']
				}
				for player in players_data if player['teamId'] == 100
			]
			red_team_players = [
				{
					'summoner_name': f"{player['riotIdGameName']}#{player['riotIdTagline']}",
					'champion_name': player['championName']
				}
				for player in players_data if player['teamId'] == 200
			]

			# team data
			teams = game_info['teams']
			blue_team = next(team for team in teams if team['teamId'] == 100)
			game_result = "Blue" if blue_team['win'] else "Red"
			
			games_info.append({
				'game_code': game_code,
				'blue_team_players': blue_team_players,
				'red_team_players': red_team_players,
				'date_played': date_played,
				'game_result': game_result
			})

		return render_template('game_history.html', games_info=games_info)
	
	except ValueError as e:
		app.logger.error(f"[!][APP][game_history][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][game_history][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('game_history.html')


# STATIC: View game data
@app.route('/game_history/<game_code>', methods=['GET'])
#@auth.login_required
@app_login_required
def view_game(game_code):
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	try:
		# if not re.match(r"^(NA1|EUW1|EUNE1|KR|BR1|JP1|LAN|LAS|OCE|TR1|RU)_\d{1,32}$", game_code):
		# 	raise ValueError("Invalid game code format.")

		if not CUSTOMS_DB.check_if_team_game_exists(game_code, session['active_team_uuid']):
			raise ValueError(f"Game {game_code} not found for current team.")

		#team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		team_game_data = CUSTOMS_DB.get_game_data_blob_by_game_id(game_code)

		if team_game_data == None:
			raise ValueError("No games found for active team.")
		
		if DEBUG:
			app.logger.debug(f"[?][APP][view_game][{session.get('username')}] Successfully fetched game data for game ID {game_code}")
		
		# Extract relevant data
		game_info = json.loads(team_game_data[0])['info']
		teams = game_info['teams']
		players_data = game_info['participants']

		# Determine the winning team
		blue_team = next(team for team in teams if team['teamId'] == 100)
		game_result = "Blue" if blue_team['win'] else "Red"

		return render_template('view_game.html', 
						 game_code=game_code, 
						 game_data=game_info, 
						 game_result=game_result, 
						 players_data=players_data)
		
	except ValueError as e:
		app.logger.error(f"[!][APP][view_game][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][view_game][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(url_for('game_history'))
	#return redirect(url_for('teams', team_uuid=session.get('active_team_uuid')))


# Static: PLAYER ROUTES
@app.route('/player_stats', methods=['GET'])
#@auth.login_required
@app_login_required
def player_stats():
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	try:
		team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		players_info = {}

		for game in team_game_data:
			# game blob data
			game_info = json.loads(game[1])['info']
			
			# player data
			players_data = game_info['participants']
			for player in players_data:
				summoner_name = f"{player['riotIdGameName']}#{player['riotIdTagline']}"
				
				if summoner_name not in players_info:
					players_info[summoner_name] = {
						'kills': 0,
						'assists': 0,
						'deaths': 0,
						'wins': 0,
						'losses': 0,
						'gold_earned': 0,
						'damage_dealt': 0
					}
				
				players_info[summoner_name]['kills'] += player['kills']
				players_info[summoner_name]['assists'] += player['assists']
				players_info[summoner_name]['deaths'] += player['deaths']
				players_info[summoner_name]['gold_earned'] += player['goldEarned']
				players_info[summoner_name]['damage_dealt'] += player['totalDamageDealtToChampions']
				
				if player['win']:
					players_info[summoner_name]['wins'] += 1
				else:
					players_info[summoner_name]['losses'] += 1


	except ValueError as e:
		app.logger.error(f"[!][APP][player_stats][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][player_stats][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('player_stats.html', players_info=players_info)


# ACTION: Manually add game stats
@app.route('/manual_game_entry', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@app_login_required
def manual_game_entry():
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	try:
		# Check that user is the captain of the team they are adding the game to
		if not CUSTOMS_DB.is_user_captain_of_team(session['user_uuid'], session['active_team_uuid']):
			raise ValueError("You must be the captain of the team to add a game manually.")

		if request.method == 'GET':
			return render_template('manual_game_entry.html', champions=DD_AGENT.get_all_champion_names())
		

		if request.method == 'POST':
			game_code = f"MANUAL_CUSTOMS_{uuid.uuid4()}"

			print(f"request.form: {request.form}")

			blue_team_players = []
			red_team_players = []

			for i in range(5):

				blue_team_players.append({
					'summonerName': request.form.get(f'blue_team_players[{i}]'),
					'championName': request.form.get(f'blue_team_players_champion[{i}]'),
					'kills': int(request.form.get(f'blue_team_players_kills[{i}]')),
					'assists': int(request.form.get(f'blue_team_players_assists[{i}]')),
					'deaths': int(request.form.get(f'blue_team_players_deaths[{i}]')),
					'goldEarned': int(request.form.get(f'blue_team_players_gold[{i}]')),
					'totalDamageDealtToChampions': int(request.form.get(f'blue_team_players_damage[{i}]'))
				})

				red_team_players.append({
					'summonerName': request.form.get(f'red_team_players[{i}]'),
					'championName': request.form.get(f'red_team_players_champion[{i}]'),
					'kills': int(request.form.get(f'red_team_players_kills[{i}]')),
					'assists': int(request.form.get(f'red_team_players_assists[{i}]')),
					'deaths': int(request.form.get(f'red_team_players_deaths[{i}]')),
					'goldEarned': int(request.form.get(f'red_team_players_gold[{i}]')),
					'totalDamageDealtToChampions': int(request.form.get(f'red_team_players_damage[{i}]'))
				})
			
			# date played (to match riot data blob format)
			current_time_seconds = time.time()
			date_played = int(current_time_seconds * 1000)

			# game result
			game_result = request.form['game_result']

			# Process and save the data
			game_data = {
				'info': {
					'gameCreation': date_played,
					'participants': [
						# Example structure for blue team players
						{
							'riotIdGameName': player['summonerName'].split('#')[0],
							'riotIdTagline': player['summonerName'].split('#')[1],
							'championName': player['championName'],
							'teamId': 100,
							'kills': int(player['kills']),
							'assists': int(player['assists']),
							'deaths': int(player['deaths']),
							'goldEarned': int(player['goldEarned']),
							'totalDamageDealtToChampions': int(player['totalDamageDealtToChampions']),
							'win': request.form.get('game_result') == 'Blue'
						} for player in blue_team_players
					] + [
						# Example structure for red team players
						{
							'riotIdGameName': player['summonerName'].split('#')[0],
							'riotIdTagline': player['summonerName'].split('#')[1],
							'championName': player['championName'],
							'teamId': 200,
							'kills': int(player['kills']),
							'assists': int(player['assists']),
							'deaths': int(player['deaths']),
							'goldEarned': int(player['goldEarned']),
							'totalDamageDealtToChampions': int(player['totalDamageDealtToChampions']),
							'win': request.form.get('game_result') == 'Red'
						} for player in red_team_players
					],
					'teams': [
						{
							'teamId': 100,
							'win': request.form.get('game_result') == 'Blue'
						},
						{
							'teamId': 200,
							'win': request.form.get('game_result') == 'Red'
						}
					]
				}
			}

			print(f"game_data: {game_data}")

			# Save to database (example function, replace with actual implementation)
			if not CUSTOMS_DB.add_game(game_code, json.dumps(game_data)):
				raise ValueError("Failed to add game data to database.")

			# add game id to team_game table
			if not CUSTOMS_DB.add_team_game(session.get('active_team_uuid'), game_code):
				raise ValueError("Failed to add game data to team.")

			flash('Game data successfully saved!', 'success')
			return render_template(url_for('game_history'))
		
	except ValueError as e:
		app.logger.error(f"[!][APP][manual_game_entry][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][manual_game_entry][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')
	
	return redirect(url_for('game_history'))


# ADMIN ROUTES
@app.route('/uhohadmin')
#@auth.login_required
@app_login_required
def uhohadmin():
	# DOUBLE CHECK FOR FUNKINESS
	if session.get('username') not in ADMINS:
		return redirect(url_for('uhoh', error_code=403))
	
	if DEBUG:
		app.logger.debug(f"[?][APP][uhohadmin][{session.get('username')}] Admin access granted.")

	try:
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

	except ValueError as e:
		app.logger.error(f"[!][APP][uhohadmin][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][uhohadmin][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('uhohadmin.html', 
						current_patch=DD_AGENT.get_current_patch(), 
						total_users=total_users, 
						total_teams=total_teams, 
						total_games=total_games, 
						uptime=uptime, 
						memory=memory, 
						cpu=cpu, 
						champions=champions, 
						items=items, 
						spells=spells, 
						runes=runes
						)

# ERROR ROUTES
@app.route('/uhoh/<int:error_code>')
#@auth.login_required
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

@app.errorhandler(429)
def too_many_requests(e):
	return redirect(url_for('uhoh', error_code=429))

@app.errorhandler(500)
def internal_server_error(e):
	return redirect(url_for('uhoh', error_code=500))


#################
# JINJA FILTERS #
#################
@app.template_filter('to_lowercase')
def to_lowercase(value):
	return value.lower()


@app.template_filter('sanitize')
def sanitize(value):
	return re.sub(r'\W+', '', value)


@app.template_filter('get_champion_image_base64')
def get_champion_image_base64(value):
	image_data = DD_AGENT.get_single_image('champion', value)['image_base64']
	return f"data:image/png;base64,{image_data}"


@app.template_filter('is_team_captain')
def is_team_captain(value):
	result = CUSTOMS_DB.is_user_captain_of_team(value, session.get('active_team_uuid')) != None
	return result


########
# MAIN #
########
if __name__ == '__main__':
	app.logger.debug(f"[?] APP DEBUG MODE: {DEBUG}")
	socketio.run(app, debug=DEBUG)

