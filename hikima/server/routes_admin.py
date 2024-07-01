
from flask import Blueprint, request, jsonify


app = Blueprint('api.admin', __name__,  url_prefix='/v1/admin')


@app.route('/auth/login', methods=['POST'])
def login():
    return jsonify({'message': 'seen as logged in'})


@app.route('/auth/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'logged out'})

