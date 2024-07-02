from gevent import monkey
monkey.patch_all()

import os
from gevent.pywsgi import WSGIServer
from hikma.server import server

http_server = WSGIServer(('0.0.0.0', int(os.environ['APP_PORT'])), server.app)
http_server.serve_forever()
