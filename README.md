# uhohcustoms
A flask based web application to archive League of Legends customs

## Flask Setup and Installation
1. Create a virtual environment in the cloned repo folder
	```sh
	cd /path/to/uhohcustoms/
	python3 -m venv venv

2. Activate the virtual environment
	```sh
	source venv/bin/activate

3. Install the dependancies
	```sh
	pip install -r requirements.txt

4. Populate the config.py file
	```sh
	cp config.py.example config.py
	vi config.py
	```

	Example config.py
	```python
from werkzeug.security import generate_password_hash

# GENERAL
APP_VERSION			= "0.1-beta"

# IMPORTANT STATS
# will weigh the score of each player for player_stats
STAT_WEIGHTS = {
    'wins': 0.5,
    'losses': -0.5,
    'kills': 0.3,
    'deaths': -0.3,
    'assists': 0.2,
    'gold_earned': 0.1,
    'damage_dealt': 0.1
}

# RIOT API CONFIGURATIONS
RIOT_API_KEY		= "RGAPI-XXXX"
RIOT_CLIENT_ID		= "PLACEHOLDER"
RIOT_CLIENT_SECRET	= "PLACEHOLDER"
RIOT_AUTH_URL		= "https://auth.riotgames.com/authorize"
RIOT_TOKEN_URL		= "https://auth.riotgames.com/token"
REDIRECT_URL		= "https://example.com/callback"
MATCH_REGION		= "AMERICAS"
SERVER_REGION		= "NA1"

# NETWORK INFO
LOCAL_HOST		= "127.0.0.1"
LOCAL_PORT		= 2999
LC_EVENT_URL		= f"https://{LOCAL_HOST}:{LOCAL_PORT}/liveclientdata"

CUSTOMS_HOST		= "127.0.0.1"
CUSTOMS_PORT		= 8000
CUSTOMS_DATA_CALLBACK	= f"http://{CUSTOMS_HOST}:{CUSTOMS_PORT}/data_callback"

# DB INFO
DB_TYPE				= "sqlite3"	# postgresql, sqlite3
DB_HOST				= "127.0.0.1"
DB_PORT				= "1433"
DB_NAME             = "customsdb"
DB_USER             = "USERNAME"
DB_PASSWORD         = "PASSWORD"

SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SECRETS
FLASK_SECRET_KEY	= "<flask_secret_key>"
SECRET_HEADER		= "<secret_header>"
ADMINS = ['<admin_username>', '<admin_username2>']
USERS = {
	"user": {
		"password": generate_password_hash("<user_password>"),
		"role": "user"
	},
	"admin": {
		"password": generate_password_hash("<admin_password>"),
		"role": "admin"
	}
}

	```	

5. Run the application via WSGI
	```sh
	gunicorn -k gevent -w 1 --bind 0.0.0.0:8000 app:app


## Agent Setup and Installation
