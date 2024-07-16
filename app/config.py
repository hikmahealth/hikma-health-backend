import os
from dotenv import load_dotenv

load_dotenv()
ENV = os.environ.get("APP_ENV", "prod")
PG_PORT=os.environ.get("DB_PORT", "5432")

print("ENV: ", os.getenv("APP_ENV"))

FLASK_DEBUG_PORT = 5000

if ENV in ("dev_local", "dev_docker", "stg"):
    if ENV in ("dev_local", "stg"):
        PG_HOST = "localhost"
    elif ENV == "dev_docker":
        PG_HOST = "db"

    PG_USER = "hikma_dev"
    # PG_PASSWORD = 'password'
    PG_PASSWORD = "96DDDDDB6425"
    PG_DB = "hikma_dev"
    FLASK_DEBUG = True
    PHOTOS_STORAGE_BUCKET = "dev-api-photos"
    EXPORTS_STORAGE_BUCKET = "dev-api-exports"
    LOCAL_PHOTO_STORAGE_DIR = "/tmp/hikma_photos"
    DEFAULT_PROVIDER_ID_FOR_IMPORT = "bd227f3d-0fbb-45c5-beed-8ce463481415"

if ENV == "prod":
    FLASK_DEBUG = False
    DATABASE_URL=os.environ.get("DATABASE_URL", None)
    if DATABASE_URL:
        # IF there is a connection string, proceed to extract the data from it
        db_proto, connection_params = DATABASE_URL.split("//");
        if db_proto != "postgresql:":
            raise Exception("Using a non postgresql database. HH only supports PostgreSQL.")
    
        credentials, url = connection_params.split("@")
        
        PG_HOST=url.split("/")[0]
        PG_DB=url.split("/")[1]
        PG_USER=credentials.split(":")[0]
        PG_PASSWORD=credentials.split(":")[1]
    else:
        PG_HOST=os.environ["DB_HOST"]
        PG_DB=os.environ["DB_NAME"]
        PG_USER=os.environ["DB_USER"]
        PG_PASSWORD=os.environ["DB_PASSWORD"]

    PHOTOS_STORAGE_BUCKET = os.environ["PHOTOS_STORAGE_BUCKET"]
    EXPORTS_STORAGE_BUCKET = os.environ["EXPORTS_STORAGE_BUCKET"]
    LOCAL_PHOTO_STORAGE_DIR = "/tmp/hikma_photos"
    DEFAULT_PROVIDER_ID_FOR_IMPORT = os.environ["DEFAULT_PROVIDER_ID"]
