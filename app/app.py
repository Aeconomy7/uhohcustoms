###########################
# the big bad app.py file #
###########################


###########
# LIBRARY #
###########
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
# from flask_httpauth import HTTPBasicAuth
# from requests.auth import HTTPBasicAuth
import base64
from flask_socketio import SocketIO, emit
#from flask_limiter import Limiter
#from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import unquote
import logging
import http.client as http_client
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
from config import *
#from db.customsdb import CustomsDbHandler
if DB_TYPE == 'sqlite3':
	from db.customsdb_sqlite3 import CustomsDbHandler
if DB_TYPE == 'postgresql':
	from db.customsdb import CustomsDbHandler
from agents.datadragon_agent import DataDragonAgent
from agents.riot_agent import RiotAgent
from agents.wu_bot_agent import WuBotAgent



#########
# FLASK #
#########
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# limiter = Limiter(
# 	get_remote_address,
# 	app=app,
# 	default_limits=["200 per day", "50 per hour"]
# )

app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=1)

##############
# BASIC AUTH #
##############
# auth = HTTPBasicAuth()

# @auth.verify_password
# def verify_password(username, password):
# 	if username in USERS and check_password_hash(USERS[username]["password"], password):
# 		return username

# @auth.get_user_roles
# def get_user_roles(username):
# 	return USERS[username]["role"] if username in USERS else None



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
RIOT_AGENT = RiotAgent(RIOT_API_KEY, RIOT_AUTH_URL, RIOT_TOKEN_URL, REDIRECT_URI)
RIOT_AGENT.__enter__()


##############
# MAIL AGENT #
##############
MAIL_AGENT = WuBotAgent()
MAIL_AGENT.__enter__()

###########
# LOGGING #
###########
if DEBUG_VERBOSE:
	http_client.HTTPConnection.debuglevel = 1

	logging.basicConfig(level=logging.DEBUG)
	logging.getLogger("http.client").setLevel(logging.DEBUG)
	logging.getLogger("urllib3").setLevel(logging.DEBUG)
	logging.getLogger("requests").setLevel(logging.DEBUG)

	logging.getLogger("chardet").setLevel(logging.INFO)
	logging.getLogger("charset_normalizer").setLevel(logging.INFO)
	logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

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
SUPPORTED_REGIONS	= ['NA1', 'EUW1', 'EUN1', 'KR', 'BR1', 'LA1', 'LA2', 'OC1', 'JP1', 'TR1', 'RU']


#####################
# UTILITY FUNCTIONS #
#####################
def get_active_page():
	return request.path

def is_user_member_of_team(user_uuid, team_uuid):
	role = CUSTOMS_DB.get_user_team_role(user_uuid, team_uuid)
	if role == 'Captain' or role == 'Member':
		return True
	return False

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


############
# WRAPPERS #
############
def app_login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'user_uuid' not in session:
			return redirect(url_for('login'))
		return f(*args, **kwargs)
	return decorated_function

# maybe will use maybe not but its here...
def team_membership_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		active_team_uuid = session.get('active_team_uuid')
		if not active_team_uuid or not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
			flash("You must be a member or captain of the active team to access this page.", "danger")
			return redirect(url_for('manage_teams'))
		
		return f(*args, **kwargs)
	return decorated_function

#############
# INJECTORS #
#############
# @app.context_processor
# def inject_active_page():
# 	return dict(get_active_page=get_active_page)

@app.context_processor
def inject_globals():
	USER_ROLE = CUSTOMS_DB.get_user_team_role(session.get('user_uuid'), session.get('active_team_uuid'))
	return dict(get_active_page=get_active_page, APP_VERSION=APP_VERSION, USER_ROLE=USER_ROLE)

@app.context_processor
def inject_enumerate():
	return dict(enumerate=enumerate)


######################
# REQUEST PROCESSING #
######################
# BEFORE #
# @app.before_request
# def limit_post_requests():
# 	if request.method == 'POST':
# 		if request.path == '/login' or request.path == '/register' or request.path == '/add_game' or request.path == 'manual_game_upload':
# 			if request.endpoint == 'login' or request.endpoint == 'register':
# 				limiter.limit("10 per minute")(lambda: None)()

# AFTER #
@app.after_request
def add_header(response):
	if request.path.startswith('/static/'):
		response.cache_control.max_age = 31536000  # Cache static files for 1 year
	return response


##########
# ROUTES #
##########
#@limiter.exempt
@app.route('/')
def index():
	return render_template('index.html')


#@limiter.exempt
@app.route('/about')
def about():
	return render_template('about.html')

#@limiter.exempt
@app.route('/terms')
def terms():
	return render_template('terms.html')

#@limiter.exempt
@app.route('/privacy')
def privacy():
	return render_template('privacy.html')

#@limiter.exempt
@app.route('/health', methods=['GET'])
def health():
	return jsonify(status="UP"), 200


# serve static routes
#@limiter.exempt
@app.route('/static/js/<path:filename>')
def custom_static(filename):
	return send_from_directory(os.path.join(app.root_path, 'static', 'js'), filename)


# STATIC: Account page
@app.route('/account', methods=['GET', 'POST'])
@app_login_required
def account():
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		user_uuid = session['user_uuid']
		user_data = CUSTOMS_DB.get_user_by_user_uuid(user_uuid)

		if request.method == 'POST':
			action = request.form.get('action')

			# Update email
			# if action == 'update_email':
			# 	new_email = request.form.get('email')
			# 	if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", new_email):
			# 		flash('Invalid email format.', 'danger')
			# 	elif CUSTOMS_DB.check_if_user_email_exists(None, new_email):
			# 		flash('Email is already in use.', 'danger')
			# 	else:
			# 		if CUSTOMS_DB.update_user_email(user_uuid, new_email):
			# 			flash('Email updated successfully.', 'success')
			# 			session['email'] = new_email
			# 		else:
			# 			flash('Failed to update email.', 'danger')

			# Update password
			# elif action == 'update_password':
			if action == 'update_password':
				current_password = request.form.get('current_password')
				new_password = request.form.get('new_password')
				confirm_password = request.form.get('confirm_password')

				if not check_password_hash(user_data[4], current_password):
					flash('Current password is incorrect.', 'danger')
				elif len(new_password) < 10:
					flash('New password must be at least 10 characters long.', 'danger')
				elif new_password != confirm_password:
					flash('New passwords do not match.', 'danger')
				else:
					new_password_hash = generate_password_hash(new_password)
					if CUSTOMS_DB.update_user_password(user_uuid, new_password_hash):
						flash('Password updated successfully.', 'success')
					else:
						flash('Failed to update password.', 'danger')

			# Link Riot account
			elif action == 'link_riot_account':
				riot_auth_url = f"{RIOT_AUTH_URL}?response_type=code&client_id={RIOT_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid"
				return redirect(riot_auth_url)
			
			elif action == 'unlink_riot_account':
				if CUSTOMS_DB.unlink_rso_account_from_user(user_uuid):
					session.pop('riot_id', None)
					session.pop('riot_puuid', None)
					session.pop('access_token', None)
					session.pop('refresh_token', None)
					flash('Riot account unlinked successfully.', 'success')
				else:
					flash('Failed to unlink Riot account.', 'danger')

		return render_template('account.html', user_data=user_data)

	except Exception as e:
		app.logger.error(f"[!][APP][account][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')
		return redirect(url_for('uhoh', error_code=500))


# ACTION: Request password reset
@app.route('/forgot_password', methods=['POST'])
def forgot_password():
	user_email = request.form.get('email')

	if not user_email or not CUSTOMS_DB.check_if_user_email_exists(None, user_email):
		flash('Invalid email address.', 'danger')
		return redirect(url_for('forgot_password_page'))

	token = MAIL_AGENT.generate_token(user_email, app.secret_key, salt=RESET_PASSWORD_SALT)
	reset_url = url_for('reset_password', token=token, _external=True)

	MAIL_AGENT.send_reset_password_email(user_email, token)

	flash('Password reset email sent. Please check your inbox.', 'info')
	return redirect(url_for('index'))


# ACTION: Reset password
# @app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
	email = MAIL_AGENT.verify_token(token, app.secret_key, salt=RESET_PASSWORD_SALT)

	if not email:
		flash('Invalid or expired token.', 'danger')
		return redirect(url_for('index'))

	if request.method == 'POST':
		new_password = request.form.get('new_password')
		confirm_password = request.form.get('confirm_password')

		if new_password != confirm_password:
			flash('Passwords do not match.', 'danger')
		elif len(new_password) < 10:
			flash('Password must be at least 10 characters long.', 'danger')
		else:
			new_password_hash = generate_password_hash(new_password)
			if CUSTOMS_DB.update_user_password_by_email(email, new_password_hash):
				flash('Password reset successfully!', 'success')
				return redirect(url_for('login'))
			else:
				flash('Failed to reset password.', 'danger')

	return render_template('reset_password.html', token=token)

# STATIC : Verify email page
# ACTION : request email verification
# @app.route('/verify_email', methods=['GET'])
# @app_login_required
# def verify_email_page():
# 	if 'user_uuid' not in session:
# 		return redirect(url_for('uhoh', error_code=401))

# 	user_uuid = session['user_uuid']
# 	user_data = CUSTOMS_DB.get_user_by_user_uuid(user_uuid)

# 	if user_data[9] == 1:
# 		flash('Your email is already verified or does not exist.', 'info')
# 		return redirect(request.args.get('next', url_for('manage_teams')))

# # ACTION: Verify email
# @app.route('/verify_email/<user_uuid>/<token_uuid>', methods=['GET'])
# def verify_email(user_uuid, token_uuid):
# 	if not user_uuid or not token_uuid:
# 		flash('Invalid verification link.', 'danger')

# ACTION: User Registration
@app.route('/register', methods=['GET','POST'])
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
	if 'user_uuid' not in session:
		flash('You must be logged in to use this feature.', 'danger')
		#return redirect(url_for('uhoh', error_code=401))
		return redirect(url_for('login'))

	riot_auth_uri = f"{RIOT_AUTH_URL}?response_type=code&client_id={RIOT_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={OAUTH2_SCOPE}"
	return redirect(riot_auth_uri)


# AUTH: Login
@app.route('/login', methods=['GET','POST'])
#@auth.login_required
def login():
	if request.method == 'POST':
		email = request.form['email']
		password = request.form['password']

		user = CUSTOMS_DB.get_user_by_email(email)

		if user	and check_password_hash(user[4], password):
			session['user_uuid'] 	= user[3]
			session['username'] 	= user[1]

			session.permanent = True

			user_teams = CUSTOMS_DB.get_teams_for_user(session['user_uuid'])

			session['user_teams'] = [{'team_uuid': team[0], 'team_name': team[1]} for team in user_teams]
			session['active_team_uuid'] = str(user_teams[0][0]) if user_teams else 'None'
			session['active_team_name'] = str(user_teams[0][1]) if user_teams else 'None'
			session['role'] = 'admin' if user[1] in ADMINS else 'user'

			if DEBUG:
				app.logger.debug(f"[?][APP][login][{session['username']}] user_teams: {str(session['user_teams'])}")
				app.logger.debug(f"[?][APP][login][{session['username']}] active_team_uuid: {str(session['active_team_uuid'])}")

			return redirect(request.args.get('next', url_for('manage_teams')))
			# if user[9] == 0:
			# 	flash('Please verify your email before logging in.', 'warning')
			# 	return redirect(url_for('verify_email'))
			# else:
			# 	return redirect(request.args.get('next', url_for('manage_teams')))
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
	if code:
		code = unquote(code)
	else:
		return redirect(url_for('login'))

	credentials = f"{RIOT_CLIENT_ID}:{RIOT_CLIENT_SECRET}"
	encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
	
	http_proxy = None
	https_proxy = None

	proxies = {
		"http": http_proxy,
		"https": https_proxy
	}
	
	headers = {
		"Content-Type": "application/x-www-form-urlencoded",
		"Authorization": f"Basic {encoded_credentials}"
	}

	data = {
		"grant_type": "authorization_code",
		"code": code,
		"redirect_uri": REDIRECT_URI,
	}

	token_response = requests.post(
		RIOT_TOKEN_URL,
		headers=headers,
		data=data,
		proxies=proxies
	)

	if token_response.status_code == 200:
		token_data = token_response.json()
		session['access_token'] = token_data['access_token']
		session['refresh_token'] = token_data['refresh_token']
		summoner_data = RIOT_AGENT.fetch_account_data(
			token=session['access_token']
		)
		if not summoner_data:
			flash('Failed to fetch summoner data. Please try again.', 'danger')
			return redirect(url_for('account'))
		if DEBUG:
			app.logger.debug(f"[?][APP][callback][{session.get('username')}] summoner_data: {summoner_data}")
		if not CUSTOMS_DB.link_rso_account_to_user(
			user_uuid=session['user_uuid'],
			riot_id=f"{summoner_data['gameName']}#{summoner_data['tagLine']}",
			riot_puuid=summoner_data['puuid'],
			access_token=session['access_token'],
			refresh_token=session['refresh_token']
		):
			flash('Failed to link RSO account. Please try again.', 'danger')
			session.pop('access_token', None)
			session.pop('refresh_token', None)
			return redirect(url_for('account'))
		else:
			flash('Successfully linked RSO account!', 'success')
			# Update the session with the new RSO data
			session['riot_id'] = f"{summoner_data['gameName']}#{summoner_data['tagLine']}"
			session['riot_puuid'] = summoner_data['puuid']
			# Redirect to manage teams or account page
			return redirect(url_for('account'))
	else:
		flash(f"Error requesting RSO token. Response code {token_response.status_code}", 'danger')
		return redirect(url_for('login'))


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
			if CUSTOMS_DB.is_user_captain_of_team(user_uuid, str(team[0])):
				captain_team = team
				break

		captain_team_members_pending = CUSTOMS_DB.get_team_members_pending(captain_team[0]) if captain_team else None

		if DEBUG:
			app.logger.debug(f"[?][APP][manage_teams][{session.get('username')}] user_teams: {user_teams}")

	except Exception as e:
		app.logger.error(f"[!][APP][manage_teams][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('manage_teams.html', 
						user_teams=user_teams, 
						captain_team=captain_team, 
						captain_team_members_pending=captain_team_members_pending
						)


# ACTION: Approve member
@app.route('/approve_member', methods=['POST'])
@app_login_required
def approve_member():
	
	try:
		team_uuid = request.form.get('team_uuid')
		user_uuid = request.form.get('user_uuid')

		if not team_uuid or not user_uuid:
			raise ValueError("Missin team_uuid or user_uuid (this shouldn't happen).")

		if not CUSTOMS_DB.is_user_captain_of_team(session['user_uuid'], team_uuid):
			raise ValueError("You are not authorized to approve members for this team.")

		if CUSTOMS_DB.approve_user_to_team(user_uuid, team_uuid):
			flash("Member approved successfully.", "success")
		else:
			raise ValueError("Failed to approve member.", "danger")

	except ValueError as e:
		app.logger.error(f"[!][APP][approve_member][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][approve_member][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(url_for('manage_teams'))


# ACTION: Reject member
@app.route('/reject_member', methods=['POST'])
@app_login_required
def reject_member():
	
	try:
		team_uuid = request.form.get('team_uuid')
		user_uuid = request.form.get('user_uuid')

		if not team_uuid or not user_uuid:
			raise ValueError("Missing team_uuid or user_uuid (this shouldn't happen).")

		if not CUSTOMS_DB.is_user_captain_of_team(session['user_uuid'], team_uuid):
			raise ValueError("You are not authorized to reject members for this team.")

		if CUSTOMS_DB.reject_user_from_team(user_uuid, team_uuid):
			flash("Member rejected successfully.", "success")
		else:
			raise ValueError("Failed to reject member.", "danger")

	except ValueError as e:
		app.logger.error(f"[!][APP][reject_member][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][reject_member][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return redirect(url_for('manage_teams'))


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
			app.logger.debug(f"[?][APP][create_team][{session['username']}] Attempting to create team {team_name}...")

		# check if already a team captain
		if CUSTOMS_DB.is_user_captain(session['user_uuid']):
			raise ValueError("You are already the captain of a team.")

		if CUSTOMS_DB.check_if_team_exists_by_team_name(team_name) != None:
			raise ValueError("Team name already exists.")

		team_uuid = uuid.uuid4()

		if not CUSTOMS_DB.register_team(team_name, team_uuid, session['user_uuid']):
			raise ValueError("Failed to create team.")

		if not CUSTOMS_DB.join_user_to_team(session['user_uuid'], team_uuid, 'Captain'):
			raise ValueError("Failed to join team.")

		session['user_teams'].append({'team_name': team_name, 'team_uuid': team_uuid})
		session['active_team_uuid'] = team_uuid
		session['active_team_name'] = team_name

		if DEBUG:
			app.logger.debug(f"[+][APP][create_team][{session['username']}] Successfully created team {team_name}:{session['active_team_uuid']}")
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
		if not CUSTOMS_DB.join_user_to_team(session['user_uuid'], team_uuid, 'Pending'):
			raise ValueError("Failed to join team.")

		# LOOK HERE FOR ERRORS WITH JOIN_TEAM IN THE FUTURE MAYBE
		session['user_teams'].append({'team_name': teamcheck[1], 'team_uuid': team_uuid})
		session['active_team_uuid'] = team_uuid
		session['active_team_name'] = teamcheck[1]

		if DEBUG:
			app.logger.debug(f"[+][APP][join_team][{session['username']}] Successfully joined team {teamcheck[1]}:{team_uuid}")
		flash(f"Your membership is now pending for team {teamcheck[1]}!", 'success')

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
	
	try:

		if team_uuid == 'None':
			raise ValueError("Invalid team to leave")
		
		if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], team_uuid):
			flash("You are not a member of this team.", "danger")
			return redirect(url_for('manage_teams'))

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


# STATIC: Team member page
# 	- redact/unredact your data on the team
#	- turn of team settings such as player score / ranking
@app.route('/team_member', methods=['GET', 'POST'])
@app_login_required
def team_member():
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		if not CUSTOMS_DB.is_user_member_of_team(session['user_uuid'], session.get('active_team_uuid')):
			flash('You do not have permission to access this page.', 'danger')
			return redirect(url_for('manage_teams'))

		if request.method == 'POST':
			action = request.form.get('action')
			if action == 'toggle_redact_summoner':
				toggle = request.form.get('toggle')
				if toggle == 'on':
					CUSTOMS_DB.add_user_to_removed_data(session.get('user_uuid'), session.get('active_team_uuid'))
					flash('Summoner name redacted successfully.', 'info')
				elif toggle == 'off':
					CUSTOMS_DB.remove_user_from_removed_data(session.get('user_uuid'), session.get('active_team_uuid'))
					flash('Summoner name unredacted successfully.', 'success')
				else:
					flash('What are you doing mate?', 'danger')
			elif action == 'toggle_player_score':
				toggle = request.form.get('toggle')
				if toggle == 'on':
					CUSTOMS_DB.set_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'), True)
					flash('Player score setting enabled.', 'success')
				elif toggle == 'off':
					CUSTOMS_DB.set_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'), False)
					flash('Player score setting disabled.', 'info')
				else:
					flash('What are you doing mate?', 'danger')


		team_games = CUSTOMS_DB.get_team_game_id_data_by_team_uuid(session.get('active_team_uuid'))
		redacted_summoners = CUSTOMS_DB.get_team_data_removed_users(session.get('active_team_uuid', 'None'))
		player_score_setting = CUSTOMS_DB.get_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'))
		
		# all includes pending users too to be rendered by the team_member page
		all_team_members = CUSTOMS_DB.get_all_team_members(session.get('active_team_uuid'))

		return render_template('team_member.html', 
						 team_games=team_games, 
						 team_members=all_team_members, 
						 redacted_summoners=redacted_summoners, 
						 player_score_setting=player_score_setting, 
						 BASE_URL=BASE_URL)

	except ValueError as e:
		app.logger.error(f"[!][APP][team_member][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][team_member][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('team_member.html')



# STATIC: Team captain page
# 	- delete games
# 	- approve/reject members
@app.route('/team_captain', methods=['GET', 'POST'])
@app_login_required
def team_captain():
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		if not CUSTOMS_DB.is_user_captain_of_team(session['user_uuid'], session.get('active_team_uuid')):
			flash('You do not have permission to access this page.', 'danger')
			return redirect(url_for('manage_teams'))

		if request.method == 'POST':
			action = request.form.get('action')
			if action == 'delete_game':
				game_id = request.form.get('game_id')
				CUSTOMS_DB.remove_team_game(session.get('active_team_uuid'), game_id)
				flash('Game deleted successfully.', 'success')
			elif action == 'remove_user':
				user_uuid = request.form.get('user_uuid')
				CUSTOMS_DB.remove_user_from_team(user_uuid, session.get('active_team_uuid'))
				flash('User removed from team successfully.', 'success')
			elif action == 'approve_user':
				user_uuid = request.form.get('user_uuid')
				CUSTOMS_DB.approve_user_to_team(user_uuid, session.get('active_team_uuid'))
				flash('User approved to team successfully.', 'success')
			elif action == 'redact_summoner':
				summoner = request.form.get('summoner')
				CUSTOMS_DB.add_user_to_removed_data(summoner, session.get('active_team_uuid'))
				flash('Summoner name redacted successfully.', 'success')
			elif action == 'unredact_summoner':
				summoner = request.form.get('summoner')
				CUSTOMS_DB.remove_user_from_removed_data(summoner, session.get('active_team_uuid'))
				flash('Summoner name unredacted successfully.', 'success')
			elif action == 'toggle_player_score':
				toggle = request.form.get('toggle')
				if toggle == 'on':
					CUSTOMS_DB.set_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'), True)
					flash('Player score setting enabled.', 'success')
				elif toggle == 'off':
					CUSTOMS_DB.set_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'), False)
					flash('Player score setting disabled.', 'info')
				else:
					flash('What are you doing mate?', 'danger')


		team_games = CUSTOMS_DB.get_team_game_id_data_by_team_uuid(session.get('active_team_uuid'))
		redacted_summoners = CUSTOMS_DB.get_team_data_removed_users(session.get('active_team_uuid', 'None'))
		player_score_setting = CUSTOMS_DB.get_player_score_setting_for_team(session.get('user_uuid'), session.get('active_team_uuid'))
		# print(f"redacted_summoners: {redacted_summoners}")
		
		# all includes pending users too to be rendered by the team_captain page
		all_team_members = CUSTOMS_DB.get_all_team_members(session.get('active_team_uuid'))

		return render_template('team_captain.html', 
						 team_games=team_games, 
						 team_members=all_team_members, 
						 redacted_summoners=redacted_summoners,
						 player_score_setting=player_score_setting,
						 BASE_URL=BASE_URL)

	except ValueError as e:
		app.logger.error(f"[!][APP][team_captain][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][team_captain][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('team_captain.html')


# ACTION: Create a season
# STATIC: List all seasons
@app.route('/seasons', methods=['GET', 'POST'])
@app_login_required
def seasons():
	try:
		if 'user_uuid' not in session:
			return redirect(url_for('uhoh', error_code=401))

		if request.method == 'POST':
			season_name = request.form.get('season_name')
			end_date = request.form.get('end_date')

			if not season_name:
				flash('Season name cannot be empty.', 'danger')
				return redirect(url_for('seasons'))

			if not re.match(r"^[a-zA-Z0-9 ]{1,32}$", season_name):
				flash('Season name must be alphanumeric, spaces only, and no more than 32 characters.', 'danger')
				return redirect(url_for('seasons'))

			season_uuid = uuid.uuid4()
			end_date_timestamp = None
			if end_date:
				try:
					end_date_timestamp = datetime.datetime.strptime(end_date, '%Y-%m-%d')
				except ValueError:
					flash('Invalid end date format. Please use YYYY-MM-DD.', 'danger')
					return redirect(url_for('seasons'))

			if CUSTOMS_DB.create_season(session['active_team_uuid'], season_uuid, season_name, end_date_timestamp):
				flash('Season created successfully.', 'success')
			else:
				flash('Failed to create season.', 'danger')

		seasons = CUSTOMS_DB.get_team_seasons()
		return render_template('seasons.html', seasons=seasons)

	except Exception as e:
		app.logger.error(f"[!][APP][seasons][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('seasons.html')


# ACTION: New Game Upload - manual and file upload
@app.route('/add_game', methods=['GET', 'POST'])
#@auth.login_required
@app_login_required
def add_game():
	if 'user_uuid' not in session or 'access_token' not in session:
		flash("You must be logged in and link your Riot account to add a game. You can do this in the Account tab in the upper right corner dropdown.", "warning")
		return redirect(url_for('uhoh', error_code=401))

	if session.get('active_team_uuid','None') == 'None':
		flash("You are not a member of any team.", "danger")
		return redirect(url_for('manage_teams'))

	if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
		flash("You are not a member of this team.", "danger")
		return redirect(url_for('manage_teams'))

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

			# # check if json file already exists
			# if os.path.exists(file_path):
			# 	with open (file_path, 'r') as f:
			# 		game_data = json.load(f)
			# 		checker = False

			# if not, attempt to fetch from riot api
			if game_data == None:	
				game_data = RIOT_AGENT.fetch_match_data(game_code, get_match_region(game_region), session.get('access_token', None))
				# if game_data:
				# 	flash(f"Game {game_code} successfully added!", 'success')
				# 	with open(file_path, 'w') as f:
				# 		json.dump(game_data, f)

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

			flash(f"Game {game_code} successfully added!", 'success')
			return redirect(url_for('game_history'))
		
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
	
	if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
		#flash("You are a pending member of this team.", "info")
		return render_template('game_history.html')
	
	try:
		team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		redacted_summoners = CUSTOMS_DB.get_team_data_removed_users(session.get('active_team_uuid', 'None'))
		games_info = []
		for game in team_game_data:
			blue_team_players = []
			red_team_players = []

			game_code = game[0]

			# game blob data
			game_info = json.loads(game[1])['info']
			
			# date played
			date_played_timestamp = game_info['gameCreation'] / 1000  # Convert milliseconds to seconds
			date_played = datetime.datetime.fromtimestamp(date_played_timestamp).strftime('%Y-%m-%d %H:%M:%S')

			# player data
			players_data = game_info['participants']
			for player in players_data:
				summoner_name = f"{player['riotIdGameName']}#{player['riotIdTagline']}"
				champion_name = player['championName']
				
				if len(redacted_summoners) > 0:
					if summoner_name in redacted_summoners[0]:
						player['riotIdGameName'] = "data"
						player['riotIdTagline'] = "redacted"
						summoner_name = f"{player['riotIdGameName']}#{player['riotIdTagline']}"

				if player['teamId'] == 100:
					blue_team_players.append({
							'summoner_name': summoner_name,
							'champion_name': champion_name
						})

				if player['teamId'] == 200:
					red_team_players.append({
							'summoner_name': summoner_name,
							'champion_name': champion_name
						})
					
			# print(f"blue_team_players: {blue_team_players}")
			# print(f"red_team_players: {red_team_players}")

			# team data
			teams = game_info['teams']
			blue_team = next(team for team in teams if team['teamId'] == 100)
			game_result = "Blue" if blue_team['win'] else "Red"
			
			games_info.append({
				'game_code': game_code,
				'blue_team_players': blue_team_players,
				'red_team_players': red_team_players,
				'date_played': date_played,
				'date_played_timestamp': date_played_timestamp,
				'game_result': game_result
			})

		#games_info = sorted(games_info, key=lambda x: x['date_played_timestamp'], reverse=True)

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
	
	if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
		#flash("You are a pending member of this team.", "info")
		return render_template('game_history.html')
	
	try:
		# if not re.match(r"^(NA1|EUW1|EUNE1|KR|BR1|JP1|LAN|LAS|OCE|TR1|RU)_\d{1,32}$", game_code):
		# 	raise ValueError("Invalid game code format.")

		if not CUSTOMS_DB.check_if_team_game_exists(game_code, session['active_team_uuid']):
			raise ValueError(f"Game {game_code} not found for current team.")

		#team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		team_game_data = CUSTOMS_DB.get_game_data_blob_by_game_id(game_code)
		redacted_summoners = CUSTOMS_DB.get_team_data_removed_users(session.get('active_team_uuid', 'None'))

		if team_game_data == None:
			raise ValueError("No games found for active team.")
		
		if DEBUG:
			app.logger.debug(f"[?][APP][view_game][{session.get('username')}] Successfully fetched game data for game ID {game_code}")
		
		# Extract relevant data
		game_info = json.loads(team_game_data[0])['info']
		teams = game_info['teams']
		players_data = game_info['participants']

		for player in players_data:
			summoner = f"{player['riotIdGameName']}#{player['riotIdTagline']}"
			
			if len(redacted_summoners) > 0:
				if summoner in redacted_summoners[0]:
					player['riotIdGameName'] = "data"
					player['riotIdTagline'] = "redacted"
			win_score = 1 if player['win'] else -1
			player['score'] = (
					win_score * STAT_WEIGHTS['wins'] +
					player['kills'] * STAT_WEIGHTS['kills'] +
					player['deaths'] * STAT_WEIGHTS['deaths'] +
					player['assists'] * STAT_WEIGHTS['assists'] +
					player['goldEarned'] * STAT_WEIGHTS['gold_earned'] +
					player['totalDamageDealtToChampions'] * STAT_WEIGHTS['damage_dealt']
				) + 500
			player['score'] = format(player['score'], '.2f')
			player['kda'] = (player['kills'] + player['assists']) / player['deaths'] if player['deaths'] > 0 else player['kills'] + player['assists']

		# Sort players by score
		players_data = sorted(players_data, key=lambda x: (-float(x['score'])))

		rank = 1
		for player in players_data:
			player['rank'] = rank
			rank += 1

		players_data = sorted(players_data, key=lambda x: (x['teamId']))

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
	
	if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
		#flash("You are a pending member of this team.", "info")
		return render_template('player_stats.html')
	
	try:
		team_game_data = CUSTOMS_DB.get_team_game_data_by_team_uuid(session.get('active_team_uuid', 'None'))
		players_info = {}
		sorted_players_info = {}
		redacted_summoners = CUSTOMS_DB.get_team_data_removed_users(session.get('active_team_uuid', 'None'))

		for game in team_game_data:
			# game blob data
			game_info = json.loads(game[1])['info']
			
			# player data
			players_data = game_info['participants']
			for player in players_data:
				summoner_name = f"{player['riotIdGameName']}#{player['riotIdTagline']}"

				if len(redacted_summoners) > 0:
					if summoner_name in redacted_summoners[0]:
						continue
				
				if summoner_name not in players_info:
					players_info[summoner_name] = {
						'total_kills': 0,
						'avg_kills': 0.0,
						'total_assists': 0,
						'avg_assists': 0.0,
						'total_deaths': 0,
						'avg_deaths': 0.0,
						'wins': 0,
						'losses': 0,
						'total_gold_earned': 0,
						'avg_gold_earned': 0,
						'total_damage_dealt': 0, 
						'avg_damage_dealt': 0,
						'score': 0,
						'games_played': 0,
						'champions': {}
					}
				
				players_info[summoner_name]['total_kills'] += player['kills']
				players_info[summoner_name]['total_assists'] += player['assists']
				players_info[summoner_name]['total_deaths'] += player['deaths']
				players_info[summoner_name]['total_gold_earned'] += player['goldEarned']
				players_info[summoner_name]['total_damage_dealt'] += player['totalDamageDealtToChampions']
				players_info[summoner_name]['games_played'] += 1
				
				if player['win']:
					players_info[summoner_name]['wins'] += 1
				else:
					players_info[summoner_name]['losses'] += 1

				champion_name = player['championName']
				if champion_name not in players_info[summoner_name]['champions']:
					players_info[summoner_name]['champions'][champion_name] = 0
				players_info[summoner_name]['champions'][champion_name] += 1
		
		for summoner_name, stats in players_info.items():
			# VERY IMPORTANT AND DYNAMIC
			total_games = stats['games_played']
			stats['avg_kills'] = f"{float(stats['total_kills']/total_games):.2f}"
			stats['avg_assists'] = f"{float(stats['total_assists']/total_games):.2f}"
			stats['avg_deaths'] = f"{float(stats['total_deaths']/total_games):.2f}"
			stats['avg_gold_earned'] = round(stats['total_gold_earned'] / total_games) if total_games > 0 else 0
			stats['avg_damage_dealt'] = round(stats['total_damage_dealt'] / total_games) if total_games > 0 else 0
			score = (
				((stats['wins'] * STAT_WEIGHTS['wins'] +
				stats['losses'] * STAT_WEIGHTS['losses'] +
				stats['total_kills'] * STAT_WEIGHTS['kills'] +
				stats['total_deaths'] * STAT_WEIGHTS['deaths'] +
				stats['total_assists'] * STAT_WEIGHTS['assists'] +
				stats['total_gold_earned'] * STAT_WEIGHTS['gold_earned'] +
				stats['total_damage_dealt'] * STAT_WEIGHTS['damage_dealt']) / total_games) + 500
			)
			players_info[summoner_name]['score'] = score
			players_info[summoner_name]['winrate'] = f"{float(stats['wins']/total_games * 100.0):.2f}%"
			players_info[summoner_name]['kda'] = (stats['total_kills'] + stats['total_assists']) / stats['total_deaths'] if stats['total_deaths'] > 0 else stats['total_kills'] + stats['total_assists']
			players_info[summoner_name]['avg_gold_earned'] = stats['avg_gold_earned'] 
			players_info[summoner_name]['avg_damage_dealt'] = stats['avg_damage_dealt'] 

			# Determine the most played champions
			max_games = max(players_info[summoner_name]['champions'].values())
			most_played_champions = [champ for champ, count in players_info[summoner_name]['champions'].items() if count == max_games]
			players_info[summoner_name]['most_played_champions'] = most_played_champions

		# Sort players by score
		sorted_players_info = dict(sorted(players_info.items(), key=lambda item: item[1]['score'], reverse=True))

	except ValueError as e:
		app.logger.error(f"[!][APP][player_stats][{session.get('username')}] {str(e)}")
		flash(str(e), 'danger')

	except Exception as e:
		app.logger.error(f"[!][APP][player_stats][{session.get('username')}] {str(e)}")
		flash('An unexpected error occurred. Please try again.', 'danger')

	return render_template('player_stats.html', players_info=sorted_players_info)


# ACTION: Manually add game stats
@app.route('/manual_game_entry', methods=['GET', 'POST'])
@app_login_required
def manual_game_entry():
	if 'user_uuid' not in session:
		return redirect(url_for('uhoh', error_code=401))
	
	if session.get('active_team_uuid','None') == 'None':
		flash("You are not a member of any team.", "danger")
		return redirect(url_for('manage_teams'))

	if session.get('active_team_uuid','None') != 'None' and not is_user_member_of_team(session['user_uuid'], session['active_team_uuid']):
		#flash("You are a pending member of this team.", "info")
		return render_template('game_history.html')
	
	try:
		# Check that user is the captain of the team they are adding the game to
		if not CUSTOMS_DB.is_user_captain_of_team(session['user_uuid'], session['active_team_uuid']):
			raise ValueError("You must be the captain of the team to add a game manually.")

		if request.method == 'GET':
			return render_template('manual_game_entry.html', champions=DD_AGENT.get_all_champion_names())

		if request.method == 'POST':
			game_code = f"MANUAL_CUSTOMS_{uuid.uuid4()}"

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

			# write game data to file
			# file_path = os.path.join("static", "game_data", sanitize_game_code(game_code) + ".json")
			# with open(file_path, 'w') as f:
			# 	json.dump(game_data, f)

			# Save to database (example function, replace with actual implementation)
			if not CUSTOMS_DB.add_game(game_code, json.dumps(game_data)):
				raise ValueError("Failed to add game data to database.")

			# add game id to team_game table
			if not CUSTOMS_DB.add_team_game(session.get('active_team_uuid'), game_code):
				raise ValueError("Failed to add game data to team.")

			flash('Game data successfully saved!', 'success')
			return redirect(url_for('game_history'))
		
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
		total_games = CUSTOMS_DB.get_total_team_games()

		# server stats
		uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
		memory = psutil.virtual_memory()
		cpu = psutil.cpu_percent(interval=1)

		# image data
		champions = DD_AGENT.get_images_by_category('champion')
		items = DD_AGENT.get_images_by_category('item')
		spells = DD_AGENT.get_images_by_category('spell')
		runes = DD_AGENT.get_images_by_category('rune')

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

@app.template_filter('is_user_verified')
def is_user_verified(value):
	if CUSTOMS_DB.is_user_verified(value):
		return True
	else:
		return False

@app.template_filter('is_team_captain')
def is_team_captain(value):
	result = CUSTOMS_DB.is_user_captain_of_team(session.get('user_uuid'), value) != None
	#print(f"[?][APP][is_team_captain] result for user {session.get('user_uuid')} captain of {value}: {result}")
	return result

@app.template_filter('is_team_member')
def is_team_member(value):
	result = False
	role = CUSTOMS_DB.get_user_team_role(session.get('user_uuid'), value)
	if role == 'Captain' or role == 'Member':
		result = True
	#print(f"[?][APP][is_team_member] result for user {session.get('user_uuid')} member of {value}: {result}")
	return result

@app.template_filter('is_rso_account_linked')
def is_rso_account_linked(value):
	if CUSTOMS_DB.is_rso_account_linked(value): 
		return True
	else:
		return False

@app.template_filter('is_rso_session_active')
def is_rso_session_active(value):
	if RIOT_AGENT.fetch_summoner_data(token=value) != None:
		return True
	else:
		return False

@app.template_filter('get_player_score_setting')
def get_player_score_setting(value):
	result = CUSTOMS_DB.get_player_score_setting_for_team(value, session.get('active_team_uuid'))
	if result == None or result == False:
		return False
	else:
		return True

########
# MAIN #
########
# if __name__ == '__main__':
# 	app.logger.debug(f"[?] APP DEBUG MODE: {DEBUG}")
# 	socketio.run(app, debug=DEBUG)

