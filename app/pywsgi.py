from gevent import monkey
monkey.patch_all()

import os
from gevent.pywsgi import WSGIServer
from app import main

http_server = WSGIServer(('0.0.0.0', int(os.environ['APP_PORT'])), main)
http_server.serve_forever()
