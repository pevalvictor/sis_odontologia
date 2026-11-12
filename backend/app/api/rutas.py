from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.configuracion import configuracion
from app.core.seguridad import cifrar_contrasena, verificar_contrasena, crear_token, decodificar_token
from app.db.sesion import obtener_sesion
from app.dependencias.seguridad import usuario_actual, exigir_permiso
from app.esquemas.datos import *
from app.modelos import *
from app.servicios.auditoria import auditar

router = APIRouter(prefix="/api")
MODULOS = ["configuracion", "usuarios_roles_permisos", "pacientes", "historia_clinica", "odontograma", "cotizaciones", "planes_tratamiento", "tratamientos_sesiones", "agenda_citas", "pagos_caja", "comprobantes_facturacion", "recetas_documentos", "archivos_clinicos", "inventario", "compras_proveedores", "reportes"]
ROLES = ["administrador", "odontologo", "recepcion", "caja", "almacen"]
intentos_login: dict[str, deque] = defaultdict(deque)

def serializar(obj, excluir=()):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in excluir}
def obtener_propio(sesion, modelo, id_, clinica_id):
    obj = sesion.scalar(select(modelo).where(modelo.id == id_, modelo.clinica_id == clinica_id))
    if not obj: raise HTTPException(404, "Registro no encontrado")
    return obj
def asignar(obj, datos: dict):
    for clave, valor in datos.items():
        if valor is not None and hasattr(obj, clave): setattr(obj, clave, valor)

@router.post("/autenticacion/registro-inicial", status_code=201)
def registro(datos: RegistroInicial, sesion: Session = Depends(obtener_sesion)):
    if sesion.scalar(select(Clinica.id).where(Clinica.ruc == datos.ruc)): raise HTTPException(409, "El RUC ya está registrado")
    try:
        clinica = Clinica(nombre_comercial=datos.nombre_comercial, razon_social=datos.razon_social, ruc=datos.ruc, correo=str(datos.correo_clinica), telefono=datos.telefono, direccion=datos.direccion)
        sesion.add(clinica); sesion.flush()
        usuario = Usuario(clinica_id=clinica.id, nombres=datos.nombres_administrador, apellidos=datos.apellidos_administrador, correo=str(datos.correo_administrador), nombre_usuario=datos.nombre_usuario, contrasena_hash=cifrar_contrasena(datos.contrasena))
        sesion.add(usuario); sesion.flush()
        for nombre in ROLES:
            rol = Rol(clinica_id=clinica.id, nombre=nombre, es_sistema=True); sesion.add(rol); sesion.flush()
            if nombre == "administrador": sesion.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))
        for i, codigo in enumerate(MODULOS):
            modulo = sesion.scalar(select(Modulo).where(Modulo.codigo == codigo))
            if not modulo: modulo = Modulo(nombre=codigo.replace("_", " ").title(), codigo=codigo, orden=i); sesion.add(modulo); sesion.flush()
            sesion.add(ClinicaModulo(clinica_id=clinica.id, modulo_id=modulo.id, activo=codigo in ("configuracion", "usuarios_roles_permisos"), fecha_activacion=datetime.now(timezone.utc) if codigo in ("configuracion", "usuarios_roles_permisos") else None))
        sesion.commit(); return {"mensaje": "Clínica y administrador registrados", "clinica_id": clinica.id}
    except IntegrityError: sesion.rollback(); raise HTTPException(409, "Correo o usuario duplicado")

@router.post("/autenticacion/iniciar-sesion", response_model=Tokens)
def login(datos: InicioSesion, request: Request, sesion: Session = Depends(obtener_sesion)):
    ip = request.client.host if request.client else "desconocida"
    ahora = datetime.now(timezone.utc)
    intentos_login[ip] = deque(x for x in intentos_login[ip] if ahora - x < timedelta(minutes=1))
    if len(intentos_login[ip]) >= 10: raise HTTPException(429, "Demasiados intentos. Intente nuevamente en un minuto")
    intentos_login[ip].append(ahora)
    consulta = select(Usuario).where(or_(Usuario.correo == datos.identificador, Usuario.nombre_usuario == datos.identificador))
    if datos.ruc: consulta = consulta.join(Clinica).where(Clinica.ruc == datos.ruc)
    usuarios = list(sesion.scalars(consulta.limit(2)))
    if len(usuarios) != 1 or not usuarios[0].estado or not verificar_contrasena(datos.contrasena, usuarios[0].contrasena_hash): raise HTTPException(401, "Credenciales inválidas")
    intentos_login[ip].clear(); u = usuarios[0]; u.ultimo_acceso = datetime.now(timezone.utc)
    access, _, _ = crear_token(u.id, u.clinica_id, "access", timedelta(minutes=configuracion.access_token_minutos))
    refresh, jti, vence = crear_token(u.id, u.clinica_id, "refresh", timedelta(days=configuracion.refresh_token_dias))
    sesion.add(SesionUsuario(usuario_id=u.id, identificador_token=jti, fecha_expiracion=vence)); auditar(sesion, u.clinica_id, u.id, "inicio_sesion", "autenticacion", "usuarios", u.id, ip=request.client.host if request.client else None); sesion.commit()
    return Tokens(access_token=access, refresh_token=refresh)

@router.post("/autenticacion/recuperar-contrasena", status_code=202)
def recuperar(_: RecuperarContrasena):
    # Respuesta neutra: evita revelar si una cuenta existe; punto preparado para proveedor de correo.
    return {"mensaje": "Si los datos corresponden a una cuenta, se enviarán instrucciones de recuperación"}

@router.post("/autenticacion/refrescar-token", response_model=Tokens)
def refrescar(datos: RefrescarToken, sesion: Session = Depends(obtener_sesion)):
    try: c = decodificar_token(datos.refresh_token)
    except ValueError as exc: raise HTTPException(401, str(exc))
    registro = sesion.scalar(select(SesionUsuario).where(SesionUsuario.identificador_token == c.get("jti"), SesionUsuario.revocada.is_(False)))
    usuario = sesion.get(Usuario, int(c.get("sub", 0)))
    if c.get("tipo") != "refresh" or not registro or not usuario or not usuario.estado: raise HTTPException(401, "Refresh token inválido")
    registro.revocada = True
    access, _, _ = crear_token(usuario.id, usuario.clinica_id, "access", timedelta(minutes=configuracion.access_token_minutos)); refresh, jti, vence = crear_token(usuario.id, usuario.clinica_id, "refresh", timedelta(days=configuracion.refresh_token_dias))
    sesion.add(SesionUsuario(usuario_id=usuario.id, identificador_token=jti, fecha_expiracion=vence)); sesion.commit(); return Tokens(access_token=access, refresh_token=refresh)

@router.post("/autenticacion/cerrar-sesion")
def logout(datos: CerrarSesion, request: Request, u: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    try: c = decodificar_token(datos.refresh_token)
    except ValueError: c = {}
    registro = sesion.scalar(select(SesionUsuario).where(SesionUsuario.identificador_token == c.get("jti"), SesionUsuario.usuario_id == u.id))
    if registro: registro.revocada = True
    auditar(sesion, u.clinica_id, u.id, "cierre_sesion", "autenticacion", "usuarios", u.id, ip=request.client.host if request.client else None); sesion.commit(); return {"mensaje": "Sesión cerrada"}

@router.get("/autenticacion/mi-perfil")
def perfil(u: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    roles = list(sesion.scalars(select(Rol.nombre).join(UsuarioRol).where(UsuarioRol.usuario_id == u.id)))
    return {**serializar(u, ("contrasena_hash",)), "roles": roles}

@router.get("/clinicas/mi-clinica")
def mi_clinica(u: Usuario = Depends(exigir_permiso("configuracion")), sesion: Session = Depends(obtener_sesion)): return serializar(sesion.get(Clinica, u.clinica_id))
@router.put("/clinicas/mi-clinica")
def editar_clinica(datos: ClinicaActualizar, u: Usuario = Depends(exigir_permiso("configuracion", "puede_editar")), sesion: Session = Depends(obtener_sesion)):
    c=sesion.get(Clinica,u.clinica_id); antes=serializar(c); asignar(c,datos.model_dump(exclude_unset=True)); auditar(sesion,u.clinica_id,u.id,"editar","configuracion","clinicas",c.id,antes,datos.model_dump(mode="json",exclude_unset=True)); sesion.commit(); return serializar(c)

@router.get("/sedes")
def sedes(u: Usuario=Depends(exigir_permiso("configuracion")), sesion:Session=Depends(obtener_sesion)): return [serializar(x) for x in sesion.scalars(select(Sede).where(Sede.clinica_id==u.clinica_id))]
@router.post("/sedes", status_code=201)
def crear_sede(datos:SedeCrear,u:Usuario=Depends(exigir_permiso("configuracion","puede_crear")),sesion:Session=Depends(obtener_sesion)):
    x=Sede(clinica_id=u.clinica_id,**datos.model_dump());sesion.add(x);sesion.flush();auditar(sesion,u.clinica_id,u.id,"crear","configuracion","sedes",x.id,nuevos=datos.model_dump(mode="json"));sesion.commit();return serializar(x)
@router.put("/sedes/{id_}")
def editar_sede(id_:int,datos:SedeActualizar,u:Usuario=Depends(exigir_permiso("configuracion","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    x=obtener_propio(sesion,Sede,id_,u.clinica_id);asignar(x,datos.model_dump(exclude_unset=True));sesion.commit();return serializar(x)
@router.delete("/sedes/{id_}")
def eliminar_sede(id_:int,u:Usuario=Depends(exigir_permiso("configuracion","puede_eliminar")),sesion:Session=Depends(obtener_sesion)):
    x=obtener_propio(sesion,Sede,id_,u.clinica_id);sesion.delete(x);sesion.commit();return {"mensaje":"Sede eliminada"}

@router.get("/usuarios")
def usuarios(u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos")),sesion:Session=Depends(obtener_sesion)): return [serializar(x,("contrasena_hash",)) for x in sesion.scalars(select(Usuario).where(Usuario.clinica_id==u.clinica_id))]
@router.post("/usuarios",status_code=201)
def crear_usuario(datos:UsuarioCrear,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_crear")),sesion:Session=Depends(obtener_sesion)):
    d=datos.model_dump(exclude={"contrasena","roles_ids"});x=Usuario(clinica_id=u.clinica_id,contrasena_hash=cifrar_contrasena(datos.contrasena),**d);sesion.add(x);sesion.flush()
    roles=list(sesion.scalars(select(Rol).where(Rol.id.in_(datos.roles_ids),Rol.clinica_id==u.clinica_id)));[sesion.add(UsuarioRol(usuario_id=x.id,rol_id=r.id)) for r in roles];auditar(sesion,u.clinica_id,u.id,"crear","usuarios_roles_permisos","usuarios",x.id,nuevos={**d,"correo":str(d["correo"])});sesion.commit();return serializar(x,("contrasena_hash",))
@router.get("/usuarios/{id_}")
def usuario(id_:int,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos")),sesion:Session=Depends(obtener_sesion)):return serializar(obtener_propio(sesion,Usuario,id_,u.clinica_id),("contrasena_hash",))
@router.put("/usuarios/{id_}")
def editar_usuario(id_:int,datos:UsuarioActualizar,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    x=obtener_propio(sesion,Usuario,id_,u.clinica_id);d=datos.model_dump(exclude_unset=True,exclude={"contrasena","roles_ids"});asignar(x,d)
    if datos.contrasena:x.contrasena_hash=cifrar_contrasena(datos.contrasena)
    if datos.roles_ids is not None:
        sesion.execute(delete(UsuarioRol).where(UsuarioRol.usuario_id==x.id)); roles=list(sesion.scalars(select(Rol).where(Rol.id.in_(datos.roles_ids),Rol.clinica_id==u.clinica_id)));[sesion.add(UsuarioRol(usuario_id=x.id,rol_id=r.id)) for r in roles]
    auditar(sesion,u.clinica_id,u.id,"editar","usuarios_roles_permisos","usuarios",x.id,nuevos={k:str(v) for k,v in d.items()});sesion.commit();return serializar(x,("contrasena_hash",))
@router.patch("/usuarios/{id_}/estado")
def estado_usuario(id_:int,datos:EstadoActualizar,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    x=obtener_propio(sesion,Usuario,id_,u.clinica_id)
    if x.id==u.id and not datos.estado:raise HTTPException(400,"No puede desactivar su propia cuenta")
    anterior=x.estado;x.estado=datos.estado;auditar(sesion,u.clinica_id,u.id,"cambiar_estado","usuarios_roles_permisos","usuarios",x.id,{"estado":anterior},{"estado":datos.estado});sesion.commit();return serializar(x,("contrasena_hash",))

@router.get("/roles")
def roles(u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos")),sesion:Session=Depends(obtener_sesion)):return [serializar(x) for x in sesion.scalars(select(Rol).where(Rol.clinica_id==u.clinica_id))]
@router.post("/roles",status_code=201)
def crear_rol(datos:RolCrear,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_crear")),sesion:Session=Depends(obtener_sesion)):
    x=Rol(clinica_id=u.clinica_id,**datos.model_dump());sesion.add(x);sesion.commit();return serializar(x)
@router.put("/roles/{id_}")
def editar_rol(id_:int,datos:RolActualizar,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    x=obtener_propio(sesion,Rol,id_,u.clinica_id);asignar(x,datos.model_dump(exclude_unset=True));auditar(sesion,u.clinica_id,u.id,"editar","usuarios_roles_permisos","roles",x.id);sesion.commit();return serializar(x)
@router.get("/permisos")
def permisos(u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos")),sesion:Session=Depends(obtener_sesion)):return [serializar(x) for x in sesion.scalars(select(Permiso))]
@router.put("/roles/{id_}/permisos")
def permisos_rol(id_:int,datos:PermisosRolActualizar,u:Usuario=Depends(exigir_permiso("usuarios_roles_permisos","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    rol=obtener_propio(sesion,Rol,id_,u.clinica_id);sesion.execute(delete(RolPermiso).where(RolPermiso.rol_id==rol.id)); ids=[p.permiso_id for p in datos.permisos];validos=set(sesion.scalars(select(Permiso.id).where(Permiso.id.in_(ids))))
    [sesion.add(RolPermiso(rol_id=rol.id,**p.model_dump())) for p in datos.permisos if p.permiso_id in validos];auditar(sesion,u.clinica_id,u.id,"cambiar_permisos","usuarios_roles_permisos","roles",rol.id);sesion.commit();return {"mensaje":"Permisos actualizados"}

@router.get("/modulos")
def modulos(_:Usuario=Depends(usuario_actual),sesion:Session=Depends(obtener_sesion)):return [serializar(x) for x in sesion.scalars(select(Modulo).where(Modulo.estado.is_(True)).order_by(Modulo.orden))]
@router.get("/clinicas/modulos")
def modulos_clinica(u:Usuario=Depends(usuario_actual),sesion:Session=Depends(obtener_sesion)):
    filas=sesion.execute(select(ClinicaModulo,Modulo).join(Modulo).where(ClinicaModulo.clinica_id==u.clinica_id).order_by(Modulo.orden));return [{**serializar(cm),"codigo":m.codigo,"nombre":m.nombre} for cm,m in filas]
@router.put("/clinicas/modulos/{modulo_id}")
def activar_modulo(modulo_id:int,datos:ModuloActualizar,u:Usuario=Depends(exigir_permiso("configuracion","puede_editar")),sesion:Session=Depends(obtener_sesion)):
    x=sesion.scalar(select(ClinicaModulo).where(ClinicaModulo.clinica_id==u.clinica_id,ClinicaModulo.modulo_id==modulo_id))
    if not x:raise HTTPException(404,"Módulo no encontrado")
    x.activo=datos.activo;x.fecha_activacion=datetime.now(timezone.utc) if datos.activo else None;auditar(sesion,u.clinica_id,u.id,"cambiar_modulo","configuracion","clinicas_modulos",x.id,nuevos={"activo":datos.activo});sesion.commit();return serializar(x)
