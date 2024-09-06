import psycopg
from hikmahealth.server import config

# print(dict(
#         host=config.PG_HOST,
#         port=config.PG_PORT,
#         database=config.PG_DB,
#         user=config.PG_USER,
#         password=config.PG_PASSWORD,))


def get_connection():
    """create a database connection instance"""
    conn = psycopg.connect(
        host=config.PG_HOST,
        port=config.PG_PORT,
        dbname=config.PG_DB,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
    )

    return conn


# Running this on test only
if config.APP_ENV == config.EnvironmentType.Local:
    # fun test connection to see it fail
    with get_connection() as conn:
        print("test connection happened")
        conn.close()
