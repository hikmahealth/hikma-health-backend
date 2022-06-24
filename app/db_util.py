from config import PG_USER, PG_PASSWORD, PG_HOST, PG_DB
import psycopg2

unix_socket = '/cloudsql/{}'.format("erad-baad7:us-east1:hikma-db")

def get_connection():
    return psycopg2.connect(host=unix_socket, database='hikmadb-dev', user='hikma_dev', password='ukCVF/Rvyd/x$y4A')
    
