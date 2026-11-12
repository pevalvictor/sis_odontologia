from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.core.configuracion import configuracion
from app.db.base import Base
from app import modelos  # noqa

config = context.config
config.set_main_option("sqlalchemy.url", configuracion.database_url)
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata = Base.metadata
def ejecutar_sin_conexion():
    context.configure(url=configuracion.database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle":"named"})
    with context.begin_transaction(): context.run_migrations()
def ejecutar_con_conexion():
    motor=engine_from_config(config.get_section(config.config_ini_section),prefix="sqlalchemy.",poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(connection=conexion,target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()
ejecutar_sin_conexion() if context.is_offline_mode() else ejecutar_con_conexion()

