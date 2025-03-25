# This is needed to make the `app:app` call available
# by the `gunicorn` call. See ./app/run.sh or ./scripts/run.sh
from hikmahealth.server.server import app
