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
	
	# NETWORK INFO
	LOCAL_HOST              = "127.0.0.1"
	LOCAL_PORT              = 2999
	LC_EVENT_URL            = f"https://{LOCAL_HOST}:{LOCAL_PORT}/liveclientdata"
	
	CUSTOMS_HOST            = "127.0.0.1"
	CUSTOMS_PORT            = 8000
	CUSTOMS_EVENT_CALLBACK  = f"http://{CUSTOMS_HOST}:{CUSTOMS_PORT}/event_callback"
	
	REGION                  = "AMERICAS"
	
	# SECRETS
	RIOT_API_KEY            = "RGAPI-XXXX"
	FLASK_SECRET_KEY        = "<flask_secret_key>"
	SECRET_HEADER           = "<secret_header>"
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
