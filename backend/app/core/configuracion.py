from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Configuracion(BaseSettings):
    nombre_app: str = "Sistema de Gestión Odontológica"
    entorno: str = "desarrollo"
    database_url: str = "postgresql+psycopg://postgres:12345678@localhost:5432/sis_odontologia"
    clave_secreta: str = "CAMBIAR_EN_PRODUCCION_POR_UNA_CLAVE_LARGA"
    algoritmo_jwt: str = "HS256"
    access_token_minutos: int = 30
    refresh_token_dias: int = 7
    origenes_cors: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @property
    def lista_origenes(self) -> list[str]:
        return [x.strip() for x in self.origenes_cors.split(",") if x.strip()]

@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()

configuracion = obtener_configuracion()

