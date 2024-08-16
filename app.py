# Library imports
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash
import requests

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


		if headers.get('X-Event-Type') == 'PLAYER_DATA':
			for p in event:
				print(f"p: {p}")
				PLAYERS_DATA.append(p)
			socketio.emit('add_player_data', event)

		elif headers.get('X-Event-Type') == 'EVENT_DATA':
			socketio.emit('event_data', event)

			# check if stats need updated

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

