from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.seguridad import decodificar_token
from app.db.sesion import obtener_sesion
from app.modelos import Usuario, UsuarioRol, Rol, RolPermiso, Permiso, Modulo, ClinicaModulo

portador = HTTPBearer()
def usuario_actual(cred: HTTPAuthorizationCredentials = Depends(portador), sesion: Session = Depends(obtener_sesion)) -> Usuario:
    try: carga = decodificar_token(cred.credentials)
    except ValueError as exc: raise HTTPException(status_code=401, detail=str(exc))
    if carga.get("tipo") != "access": raise HTTPException(status_code=401, detail="Se requiere access token")
    usuario = sesion.get(Usuario, int(carga["sub"]))
    if not usuario or not usuario.estado or usuario.clinica_id != carga.get("clinica_id"):
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    return usuario

def exigir_permiso(codigo_modulo: str, accion: str = "puede_ver"):
    def validar(usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)) -> Usuario:
        activo = sesion.scalar(select(ClinicaModulo.id).join(Modulo).where(ClinicaModulo.clinica_id == usuario.clinica_id, Modulo.codigo == codigo_modulo, ClinicaModulo.activo.is_(True)))
        if not activo: raise HTTPException(status_code=403, detail="Módulo no habilitado para la clínica")
        es_admin = sesion.scalar(select(Rol.id).join(UsuarioRol).where(UsuarioRol.usuario_id == usuario.id, Rol.nombre == "administrador", Rol.estado.is_(True)))
        if es_admin: return usuario
        permitido = sesion.scalar(select(RolPermiso.id).join(UsuarioRol, UsuarioRol.rol_id == RolPermiso.rol_id).join(Permiso).join(Modulo).where(UsuarioRol.usuario_id == usuario.id, Modulo.codigo == codigo_modulo, getattr(RolPermiso, accion).is_(True)))
        if not permitido: raise HTTPException(status_code=403, detail="Permiso insuficiente")
        return usuario
    return validar

