#!/bin/bash

# This script exists for backcompatibility reasons. 
# Avoid making any changes/improvement here, but instead use
#
# cd <PROJECT_ROOT_DIR>
# ./scripts/run.sh

echo -e "This script is deprecated. Please follow new instructions from README on how to run the project"
sleep 3

export PYTHONUNBUFFERED=TRUE

# Determine the correct path to run_migrations.sh
if [ -f "./scripts/run_migrations.sh" ]; then
    MIGRATION_SCRIPT="./scripts/run_migrations.sh"
    ./scripts/run_migrations.sh
    ./scripts/run.sh
elif [ -f "./run_migrations.sh" ]; then
    MIGRATION_SCRIPT="./run_migrations.sh"
    cd ..
    ./scripts/run_migrations.sh
    ./scripts/run.sh
else
    echo "Error: Please run the commands from the root folder of the hikma health backend"
    exit 1
fi


# case ${APP_ENV} in
#     prod)
#         # ./cloud_sql_proxy -instances=${DB_INSTANCE}=tcp:5432 -credential_file=${GOOGLE_APPLICATION_CREDENTIALS} &
#         # sleep 5 && 
#         APP_PORT=8000 python3 pywsgi.py
#         ;;
#     dev_docker)
#         gunicorn --timeout 6000 --access-logfile - --error-logfile - --log-level debug -w 1 -b 0.0.0.0:8080 hikmahealth:server.server.app
#         ;;
#     stg)
#         gunicorn --timeout 6000 --access-logfile - --error-logfile - --log-level debug -w 1 -b 0.0.0.0:42069 app:app
#         ;;
#     *)
#         APP_PORT=8000 python3 pywsgi.py
#         ;;
# esac
