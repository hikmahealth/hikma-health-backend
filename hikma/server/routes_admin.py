
from flask import Blueprint, request, jsonify


app = Blueprint('api-admin', __name__)


@app.route('/auth/login', methods=['POST'])
def login():
    return jsonify({'message': 'seen as logged in'})


@app.route('/auth/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'logged out'})

