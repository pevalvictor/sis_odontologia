from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.configuracion import configuracion

motor = create_engine(configuracion.database_url, pool_pre_ping=True)
SesionLocal = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)

def obtener_sesion():
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()

