# from itsdangerous import URLSafeTimedSerializer
# from flask import url_for
# from flask_mail import Message
# from app import mail

# def generate_token(email, secret_key, salt):
#     serializer = URLSafeTimedSerializer(secret_key)
#     return serializer.dumps(email, salt=salt)

# def verify_token(token, secret_key, salt, expiration=3600):
#     serializer = URLSafeTimedSerializer(secret_key)
#     try:
#         email = serializer.loads(token, salt=salt, max_age=expiration)
#         return email
#     except Exception:
#         return None
    
# def send_email(subject, recipient, html_body):
#     msg = Message(subject, recipients=[recipient], html=html_body)
#     mail.send(msg)