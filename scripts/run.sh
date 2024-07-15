#!/bin/bash

./run_migrations.sh

export PYTHONUNBUFFERED=TRUE

case ${APP_ENV} in
    prod)
        APP_PORT=8000 python3.11 pywsgi.py
        ;;
    dev_docker)
        gunicorn --timeout 6000 --access-logfile - --error-logfile - --log-level debug -w 1 -b 0.0.0.0:8080 app:app
        ;;
    stg)
        gunicorn --timeout 6000 --access-logfile - --error-logfile - --log-level debug -w 1 -b 0.0.0.0:42069 app:app
        ;;
    *)
        APP_PORT=8000 python3.11 pywsgi.py
        ;;
esac
