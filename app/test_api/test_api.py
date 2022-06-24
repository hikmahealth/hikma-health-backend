from flask import Blueprint, request, jsonify
from web_util import assert_data_has_keys
from users.user import User
from config import PG_USER, PG_PASSWORD, PG_HOST, PG_DB
from db_util import get_connection

test_api = Blueprint('test_api', __name__, url_prefix='/api/test')


@test_api.route('/getEvan', methods=['GET'])
def gea():
    alis = User.getTheUser()
    lis = {'PG_USER': PG_USER,'PG_PASSWORD':PG_PASSWORD,'PG_HOST':PG_HOST,'PG_DB':PG_DB}
    return jsonify(lis)

@test_api.route('/postEvan', methods=['POST'])
def ea():
    #alis = User.getTheUser()
    obj = request.get_json(force=True, silent=True)
    clientID = obj.get('username')
    return jsonify({'PG_USER': clientID})
