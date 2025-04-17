from flask import Flask, jsonify
from flask_cors import CORS
import logging

from hikmahealth.server import (
    custom_routes_admin,
    routes_admin_configuration,
    routes_mobile,
    routes_admin,
    test_routes,
)

from hikmahealth.server.client.keeper import register_keeper
from hikmahealth.server.client.resources import register_resource_manager
from hikmahealth.utils.errors import WebError

app = Flask(__name__)
app.url_map.strict_slashes = False

CORS(app)
# CORS(app, resources={r"/*": {"origins": "*"}})

register_keeper(app)
register_resource_manager(app)


# for backcompat
app.register_blueprint(routes_mobile.backcompatapi)
app.register_blueprint(routes_admin.admin_api)
# --------------------------------

app.register_blueprint(routes_admin.api, url_prefix='/v1/admin')
app.register_blueprint(
    routes_admin_configuration.api, url_prefix='/v1/admin/configurations'
)
app.register_blueprint(routes_mobile.api, url_prefix='/v1/api')
app.register_blueprint(test_routes.api, url_prefix='/v1/test')
# user admin extension routes
# app.register_blueprint(custom_routes_admin.api, url_prefix="/v1/admin")


@app.route('/')
def hello_world():
    return jsonify({'message': 'Welcome to the Hikma Health backend.', 'status': 'OK'})


@app.errorhandler(WebError)
def handle_web_error(error):
    logging.error(f'WebError: {error}')
    return jsonify(error.to_dict()), error.status_code


@app.errorhandler(404)
def page_not_found(_err):
    response = jsonify({'message': 'Endpoint not found.'})
    response.status_code = 404
    logging.error(f'Endpoint not found: {_err}')
    return response


@app.errorhandler(405)
def method_not_found(_err):
    response = jsonify({'message': 'Method not found.'})
    response.status_code = 405
    logging.error(f'Method not found: {_err}')
    return response


@app.errorhandler(500)
def internal_server_error(_err):
    logging.error(f'Internal Server Error: {_err}')
    return jsonify({'message': 'Internal Server Error'}), 500
