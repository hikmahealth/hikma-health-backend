from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from hikmahealth.server import config as srvconfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Connection string modified to use psycopg version 3
# https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#dialect-postgresql-psycopg-connect
if srvconfig.PG_PORT is None:
	conn_url = f'postgresql+psycopg://{srvconfig.PG_USER}:{srvconfig.PG_PASSWORD}@{srvconfig.PG_HOST}/{srvconfig.PG_DB}'
else:
	conn_url = f'postgresql+psycopg://{srvconfig.PG_USER}:{srvconfig.PG_PASSWORD}@{srvconfig.PG_HOST}:{srvconfig.PG_PORT}/{srvconfig.PG_DB}'

config.set_main_option('sqlalchemy.url', conn_url)


def run_migrations_offline():
	"""Run migrations in 'offline' mode.

	This configures the context with just a URL
	and not an Engine, though an Engine is acceptable
	here as well.  By skipping the Engine creation
	we don't even need a DBAPI to be available.

	Calls to context.execute() here emit the given string to the
	script output.

	"""
	url = config.get_main_option('sqlalchemy.url')
	context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online():
	"""Run migrations in 'online' mode.

	In this scenario we need to create an Engine
	and associate a connection with the context.

	"""
	connectable = engine_from_config(
		config.get_section(config.config_ini_section),
		prefix='sqlalchemy.',
		poolclass=pool.NullPool,
	)

	with connectable.connect() as connection:
		context.configure(connection=connection, target_metadata=target_metadata)

		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
