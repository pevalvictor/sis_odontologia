from sqlalchemy.orm import Session
from app.modelos import BitacoraAuditoria
def auditar(sesion: Session, clinica_id: int, usuario_id: int | None, accion: str, modulo: str, entidad: str, entidad_id=None, anteriores=None, nuevos=None, ip=None):
    sesion.add(BitacoraAuditoria(clinica_id=clinica_id, usuario_id=usuario_id, accion=accion, modulo=modulo, entidad=entidad, entidad_id=str(entidad_id) if entidad_id else None, datos_anteriores=anteriores, datos_nuevos=nuevos, direccion_ip=ip))

