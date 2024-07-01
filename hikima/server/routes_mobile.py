
from flask import Blueprint, jsonify


app = Blueprint('api.mobile', __name__,  url_prefix='/v1/api')

@app.route('/instance', methods=['POST'])
def login():
    return jsonify(
        [
            {"name": "Demo Instance", "url": "https://demo-api.hikmahealth.org"},
            {"name": "EMA", "url": "https://ema-api.hikmahealth.org"},
            {"name": "Local (testing)", "url": "http://192.168.86.250:8080"},
        ]
    )


@app.route('/user/reset_password', methods=['POST'])
def sync():
    """to implement what's in /app/user_api/user_api.py"""
    pass
