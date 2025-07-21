import os
import jwt
import datetime
from flask import request, jsonify

SECRET_KEY = os.getenv("SECRET_KEY")

def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def jwt_required(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        try:
            token = auth_header.split()[1]
            decoded = decode_token(token)
            if not decoded:
                return jsonify({'error': 'Invalid or expired token'}), 401
            request.user_id = decoded["user_id"]
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper
