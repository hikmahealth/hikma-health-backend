from flask import Flask, jsonify
from flask_cors import CORS

from hikmahealth.server import routes_mobile, routes_admin

from hikmahealth.utils.errors import WebError

app = Flask(__name__)
CORS(app)
app.url_map.strict_slashes = False


# for backcompat
app.register_blueprint(routes_mobile.backcompatapi)
app.register_blueprint(routes_admin.admin_api)
# --------------------------------

app.register_blueprint(routes_admin.api, url_prefix='/v1/admin')
app.register_blueprint(routes_mobile.api, url_prefix="/v1/api")


@app.route("/")
def hello_world():
    return jsonify({"message": "Welcome to the Hikma Health backend.", "status": "OK"})


@app.errorhandler(WebError)
def handle_web_error(error):    
    return jsonify(error.to_dict()), error.status_code


@app.errorhandler(404)
def page_not_found(_err):
    response = jsonify({"message": "Endpoint not found."})
    response.status_code = 404
    return response


@app.errorhandler(405)
def method_not_found(_err):
    return jsonify({"message": "Method not found."}), 405


@app.errorhandler(500)
def internal_server_error(_err):
    return jsonify({"message": "Internal Server Error"}), 500

