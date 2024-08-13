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
active_match_id = None
provider_id = 1
callback_url = "http://uhohcustoms.greatsea.online/tournament_callback"
proxies = None
#proxies = { "http": "http://192.168.69.50:8080", "https": "http://192.168.69.50:8080" }
live_game_events = []


#####################
# UTILITY FUNCTIONS #
#####################
def get_headers():
	return {
		"X-Riot-Token": RIOT_API_KEY,
		"Content-Type": "application/json"
	}

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


@app.route('/game_result_callback', methods=['POST'])
def tournament_callback():
	data = request.json

#	match_id = data.get('match_id')
#	tournament_id = data.get('tournament_id')
#	game_id = data.get('game_id')
#	winning_team = data.get('winning_team')
#	losing_team = data.get('losing_team')
#	metadata = data.get('metadata', '')

#	print(f"[?] Received callback from Riot: {str(data)}")

#	CUSTOMS_DB.insert_match(match_id, tournament_id, game_id, winning_team, losing_team, metadata)

	return 'THANKS RIOT'

# Get match events
@app.route('/event_callback', methods=['POST'])
def event_callback():
	global live_game_events

	event = request.json
	headers = request.headers

	if headers.get('X-Agent-Secret') == SECRET_HEADER:
		print(f"[?] Received callback from Game Agent: {str(event)}")

		live_game_events.append(event)

		socketio.emit('new_event', event)

		return jsonify({'status': 'THANKS FOR YOUR EVENT CONTRIBUTION AGENT'}), 200
	else:
		return jsonify({'error': 'Unauthorized'}), 403


# Watch live game updates
@app.route('/live_game', methods=['GET'])
def live_game():
	return render_template('live_game.html')


@app.route('/customs_history', methods=['GET'])
@auth.login_required
def customs_history():
	global active_tournament_id

	match_history = CUSTOMS_DB.get_match_history()

	return render_template('match_history.html', tournament_id=active_tournament_id, match_history=match_history)

# End the tournament
@app.route('/end_tournament', methods=['POST'])
@auth.login_required
def end_tournament():
	global active_tournament_id

	role = get_user_roles(auth.current_user())
	if role != "admin":
		return jsonify({"error": "Unauthorized access"}), 403

	# Logic to end the tournament and reset active_tournament_id
	if active_tournament_id:
		active_tournament_id = None
		flash('The tournament has been ended successfully.')
	else:
		flash('No active tournament to end.')

	return redirect(url_for('index'))


########
# MAIN #
########
if __name__ == '__main__':
	socketio.run(app, debug=True)


# UNUSED TOURNAMENT CODE FOR FUTURE REFERENCE

#@app.route('/create_tournament', methods=['GET', 'POST'])
##@auth.login_required
#def create_tournament():
#	global active_tournament_id
#	global callback_url
#	print(f"[!] Enter CREATE_TOURNAMENT, active_tournament_id: {active_tournament_id}")
#
#	if active_tournament_id is not None:
#		flash(f'An active tournament is already running with ID: {active_tournament_id}')
#		return redirect(url_for('track_tournament', tournament_id=active_tournament_id))
#
#	if request.method == 'POST':
#		tournament_name = request.form['tournament_name']
#
#		tournament_payload = {
#			"name": tournament_name,
#			"providerId": provider_id
#		}
#		tournament_response = requests.post(
#			"https://americas.api.riotgames.com/lol/tournament-stub/v5/tournaments",
#			headers=get_headers(),
#			json=tournament_payload,
#			proxies=proxies
#		)
#
#		if tournament_response.status_code == 200:
#			active_tournament_id = tournament_response.json()
#			flash(f'Tournament created successfully with ID: {active_tournament_id}')
#			return redirect(url_for('track_tournament', tournament_id=active_tournament_id))
#		else:
#			flash('Error creating tournament.')
#
#	return render_template('create_tournament.html')
#
#
#@app.route('/track_tournament/<tournament_id>', methods=['GET', 'POST'])
#@auth.login_required
#def track_tournament(tournament_id):
#	global active_tournament_id
#
#	print(f"[!] Enter TRACK_TOURNAMENT, active_tournament_id: {active_tournament_id}")
#
#	if request.method == 'POST':
#		# Step 3: Create a tournament code
#		map_type = request.form['map_type']
#		team_size = int(request.form['team_size'])
#		spectator_type = request.form['spectator_type']
#		pick_type = request.form['pick_type']
#
#		tournament_code_payload = {
#			"mapType": map_type,
#			"pickType": pick_type,
#			"spectatorType": spectator_type,
#			"teamSize": team_size,
#			"metadata": "UH OH CUSTOMS!",
#			"allowedSummonerIds": {}
#		}
#
#		print(f"[?] tournament_code_payload: {tournament_code_payload}")
#
#		tournament_code_response = requests.post(
#			f"https://americas.api.riotgames.com/lol/tournament-stub/v5/codes?tournamentId={tournament_id}",
#			headers=get_headers(),
#			json=tournament_code_payload,
#			proxies=proxies
#		)
#
#		print(f"[?] Create tournament request: {tournament_code_response.json()}")
#		if tournament_code_response.status_code == 200:
#			tournament_codes = tournament_code_response.json()
#			flash(f'Tournament codes generated: {tournament_codes}')
#		else:
#			flash('Error generating tournament codes.')
#
#	return render_template('track_tournament.html', tournament_id=active_tournament_id)
#
#
