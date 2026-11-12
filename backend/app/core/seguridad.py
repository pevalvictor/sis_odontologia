from datetime import datetime, timedelta, timezone
from uuid import uuid4
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.configuracion import configuracion

contexto = CryptContext(schemes=["bcrypt"], deprecated="auto")

def cifrar_contrasena(valor: str) -> str:
    return contexto.hash(valor)

def verificar_contrasena(valor: str, hash_: str) -> bool:
    return contexto.verify(valor, hash_)

def crear_token(usuario_id: int, clinica_id: int, tipo: str, duracion: timedelta) -> tuple[str, str, datetime]:
    vence = datetime.now(timezone.utc) + duracion
    identificador = str(uuid4())
    carga = {"sub": str(usuario_id), "clinica_id": clinica_id, "tipo": tipo, "jti": identificador, "exp": vence}
    return jwt.encode(carga, configuracion.clave_secreta, algorithm=configuracion.algoritmo_jwt), identificador, vence

def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, configuracion.clave_secreta, algorithms=[configuracion.algoritmo_jwt])
    except JWTError as exc:
        raise ValueError("Token inválido o vencido") from exc

