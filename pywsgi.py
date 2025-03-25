from gevent import monkey

monkey.patch_all()

import os
from gevent.pywsgi import WSGIServer
from hikmahealth.server import server, config

print('running as', config.APP_ENV)
print('on port', config.PG_PORT)
if config.APP_ENV == config.EnvironmentType.Local:
	server.app.run(
		debug=config.FLASK_DEBUG, host='0.0.0.0', port=config.FLASK_DEBUG_PORT
	)
else:
	http_server = WSGIServer(('0.0.0.0', int(os.environ['APP_PORT'])), server.app)
	http_server.serve_forever()
