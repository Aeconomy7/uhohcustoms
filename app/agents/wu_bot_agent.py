from itsdangerous import URLSafeTimedSerializer
from flask import url_for
from flask_mail import Message
from config import DEBUG, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER

class WuBotAgent:
	def __init__(self):
		return
	
	def __enter__(self):
		return
	   
	def generate_token(email, secret_key, salt):
		serializer = URLSafeTimedSerializer(secret_key)
		return serializer.dumps(email, salt=salt)

	def verify_token(token, secret_key, salt, expiration=3600):
		serializer = URLSafeTimedSerializer(secret_key)
		try:
			email = serializer.loads(token, salt=salt, max_age=expiration)
			return email
		except Exception:
			return None
		
	def send_email(subject, recipient, html_body):
		msg = Message(subject, recipients=[recipient], html=html_body)
		mail.send(msg)

	def send_reset_password_email(self, email, token):
		msg = Message(
			"Password Reset Confirmation",
			recipients=[email],
			html=f"""
				<p>Salutations!</p>
				<p>Old monkey heard your forgot your secret word of passing, I have something that might help:</p>
				<a href="{url_for('auth.reset_with_token', token=token, _external=True)}">Reset Password</a>
				<p>This magic link will expire in 15 minutes.</p>
			"""
		)