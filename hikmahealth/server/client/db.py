import psycopg
from hikmahealth.server import config

import psycopg
# from psycopg.pool import ConnectionPool
from psycopg_pool import ConnectionPool
from hikmahealth.server import config
import logging

# _pool = None


# def get_connection_pool():
#     global _pool
#     if _pool is None:
#         try:
#             _pool = ConnectionPool(
#                 min_size=1,
#                 max_size=10,
#                 conninfo=dict(
#                     host=config.PG_HOST,
#                     port=config.PG_PORT,
#                     dbname=config.PG_DB,
#                     user=config.PG_USER,
#                     password=config.PG_PASSWORD,
#                     connect_timeout=10
#                 )
#             )
#         except Exception as e:
#             logging.error(f"Failed to create connection pool: {e}")
#             raise

#     return _pool


# def get_connection():
#     """Get a database connection from the pool with automatic reconnection"""
#     try:
#         pool = get_connection_pool()
#         return pool.getconn()
#     except Exception as e:
#         logging.error(f"Database connection error: {e}")
#         raise psycopg.OperationalError(
#             "Failed to establish database connection")

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
