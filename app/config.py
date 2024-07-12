import os
from dotenv import load_dotenv

load_dotenv()
ENV = os.environ.get("APP_ENV", "dev_local")

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
    PG_USER = os.environ["dbname_pzgj_user"]
    # PG_USER = os.environ["DB_NAME"]
    PG_PASSWORD = os.environ["LvPJ30H7dQi14p4AiO9mXD9kOObCrUl9"]
    PG_HOST = os.environ["dpg-cq8ep06ehbks738ig89g-a"]
    # PG_HOST = 'localhost'
    PG_DB = os.environ["dbname_pzgj"]
    PHOTOS_STORAGE_BUCKET = os.environ[""]
    EXPORTS_STORAGE_BUCKET = os.environ[""]
    LOCAL_PHOTO_STORAGE_DIR = "/tmp/hikma_photos"
    DEFAULT_PROVIDER_ID_FOR_IMPORT = os.environ[""]
