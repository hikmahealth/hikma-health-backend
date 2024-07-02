import psycopg
from hikma.server import config

# print(dict(
#         host=config.PG_HOST, 
#         database=config.PG_DB, 
#         user=config.PG_USER, 
#         password=config.PG_PASSWORD,))

def get_connection():
    """create a database connection instance"""
    return psycopg.connect(
        host=config.PG_HOST, 
        database=config.PG_DB, 
        user=config.PG_USER, 
        password=config.PG_PASSWORD,
    )