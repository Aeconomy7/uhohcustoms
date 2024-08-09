from flask import Flask, render_template, request, redirect, url_for, flash
from flask_httpauth import HTTPBasicAuth
import requests
from config import RIOT_API_KEY, REGION, USERS

#########
# FLASK #
#########
app = Flask(__name__)
app.secret_key = "sc00by_rocks"  # Change this to a secure key

auth = HTTPBasicAuth()

###########
# GLOBALS #
###########
active_tournament_id = None


#####################
# UTILITY FUNCTIONS #
#####################
def get_headers():
	return {
		"X-Riot-Token": RIOT_API_KEY,
		"Content-Type": "application/json"
	}


##########
# ROUTES #
##########
@app.route('/')
@auth.login_required
def index():
	return render_template('index.html')


@app.route('/create_tournament', methods=['GET', 'POST'])
@auth.login_required
def create_tournament():
	global active_tournament_id

	if active_tournament_id is not None:
		flash(f'An active tournament is already running with ID: {active_tournament_id}')
		return redirect(url_for('track_tournament', tournament_id=active_tournament_id))

	if request.method == 'POST':
		tournament_name = request.form['tournament_name']
		provider_url = request.form['provider_url']

		# Step 1: Register a provider
		provider_payload = {
			"region": REGION,
			"url": provider_url
		}
		provider_response = requests.post(
			"https://americas.api.riotgames.com/lol/tournament-stub/v4/providers",
			headers=get_headers(),
			json=provider_payload
		)

		if provider_response.status_code == 200:
			provider_id = provider_response.json()

			# Step 2: Create a tournament
			tournament_payload = {
				"name": tournament_name,
				"providerId": provider_id
			}
			tournament_response = requests.post(
				"https://americas.api.riotgames.com/lol/tournament-stub/v4/tournaments",
				headers=get_headers(),
				json=tournament_payload
			)

			if tournament_response.status_code == 200:
				tournament_id = tournament_response.json()
				flash(f'Tournament created successfully with ID: {tournament_id}')
				return redirect(url_for('track_tournament', tournament_id=tournament_id))
			else:
				flash('Error creating tournament.')
		else:
			flash('Error registering provider.')
	return render_template('create_tournament.html')


@app.route('/track_tournament/<tournament_id>', methods=['GET', 'POST'])
@auth.login_required
def track_tournament(tournament_id):
	if request.method == 'POST':
		# Step 3: Create a tournament code
		map_type = request.form['map_type']
		team_size = int(request.form['team_size'])
		spectator_type = request.form['spectator_type']
		pick_type = request.form['pick_type']

		tournament_code_payload = {
			"mapType": map_type,
			"pickType": pick_type,
			"spectatorType": spectator_type,
			"teamSize": team_size,
			"metadata": "Custom metadata",
			"allowedSummonerIds": [],  # Optionally restrict who can join
		}

		tournament_code_response = requests.post(
			f"https://americas.api.riotgames.com/lol/tournament-stub/v4/codes?tournamentId={tournament_id}",
			headers=get_headers(),
			json=[tournament_code_payload]
		)

		if tournament_code_response.status_code == 200:
			tournament_codes = tournament_code_response.json()
			flash(f'Tournament codes generated: {tournament_codes}')
		else:
			flash('Error generating tournament codes.')

	return render_template('track_tournament.html', tournament_id=tournament_id)


@app.route('/tournament_detail/<tournament_id>')
@auth.login_required
def tournament_detail(tournament_id):
	# Example of retrieving match history or additional details about the tournament
	# Replace with actual logic as needed
	match_history = []  # Fetch from a database or API if tracking matches
	return render_template('tournament_detail.html', tournament_id=tournament_id, match_history=match_history)

@app.route('/end_tournament', methods=['POST'])
@auth.login_required
def end_tournament():
	global active_tournament_id

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
	app.run(debug=True)
