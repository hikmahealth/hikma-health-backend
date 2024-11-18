"""
All configurations needed by the server to run must be loaded here.

To allow loading of the environment variable from possibly different named path,
run the project using the `dotenv[cli]` as opposed to using
`from dotenv import load_dotenv`

---

Because some of the dependencies are needed by the server to run, the code must fail
and stopped running any further
"""

# added to support back compat as
# .env might be in the <PROJECT_ROOT>/app
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv("app/.env")

# preferably control how the environment variables are injected.
# This is left here for familiarity reasons. This should be removed
# -------


class EnvironmentType:
    """Different environment expected to run in the application"""

    Prod = "prod"
    Staging = "stg"
    Local = "dev_local"
    Docker = "dev_docker"


# for PostgreSQL connection
DATABASE_URL = os.environ.get("DATABASE_URL", None)

# This might be an azure connection string for the database
DATABASE_URL_AZURE = os.environ.get("AZURE_POSTGRESQL_CONNECTIONSTRING", None)

# If database_url is present use it.
if DATABASE_URL:
    # IF there is a connection string, proceed to extract the data from it
    db_proto, connection_params = DATABASE_URL.split("//")
    if db_proto != "postgresql:":
        raise Exception(
            "Using a non postgresql database. HH only supports PostgreSQL.")

    credentials, url = connection_params.split("@")

    PG_HOST = url.split("/")[0]
    PG_DB = url.split("/")[1]
    PG_USER = credentials.split(":")[0]
    PG_PASSWORD = credentials.split(":")[1]
# if database_url_azure is present use it.
elif DATABASE_URL_AZURE:
    conn_str_params = {
        pair.split("=")[0]: pair.split("=")[1] for pair in DATABASE_URL_AZURE.split(" ")
    }
    PG_USER = conn_str_params["user"]
    PG_PASSWORD = conn_str_params["password"]
    PG_HOST = conn_str_params["host"]
    PG_DB = conn_str_params["dbname"]
    EXPORTS_STORAGE_BUCKET = "dev-api-exports"
    LOCAL_PHOTO_STORAGE_DIR = "/tmp/hikma_photos"
else:
    PG_HOST = os.environ["DB_HOST"]
    PG_DB = os.environ["DB_NAME"]
    PG_USER = os.environ["DB_USER"]
    PG_PASSWORD = os.environ["DB_PASSWORD"]

PG_PORT = os.environ.get("DB_PORT", "5432")

APP_ENV = os.environ.get("APP_ENV", EnvironmentType.Prod)
# APP_ENV = os.environ["APP_ENV"]

FLASK_DEBUG = True
FLASK_DEBUG_PORT = int(os.environ.get("FLASK_DEBUG_PORT", "5000"))

if APP_ENV == EnvironmentType.Prod:
    FLASK_DEBUG = False
    FLASK_DEBUG_PORT = None

# DEFAULT_PROVIDER_ID_FOR_IMPORT = os.environ["DEFAULT_PROVIDER_ID"]

PHOTOS_STORAGE_BUCKET = os.environ.get("PHOTOS_STORAGE_BUCKET")
EXPORTS_STORAGE_BUCKET = os.environ.get("EXPORTS_STORAGE_BUCKET")
LOCAL_PHOTO_STORAGE_DIR = os.environ.get(
    "LOCAL_PHOTO_STORAGE_DIR", "/tmp/hikma_photos")
