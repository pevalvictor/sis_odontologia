from sqlalchemy import select
from app.db.sesion import SesionLocal
from app.core.seguridad import cifrar_contrasena
from app.modelos import Clinica, Usuario, Rol, UsuarioRol, Modulo, Permiso, ClinicaModulo, RolPermiso, Sede, Consultorio, TipoCita
from app.api.rutas import MODULOS, ROLES

def ejecutar():
    with SesionLocal() as s:
        modulos=[]
        for i,codigo in enumerate(MODULOS):
            m=s.scalar(select(Modulo).where(Modulo.codigo==codigo))
            if not m: m=Modulo(nombre=codigo.replace("_"," ").title(),codigo=codigo,orden=i);s.add(m);s.flush()
            modulos.append(m)
            for accion in ("ver","crear","editar","eliminar","exportar"):
                cod=f"{codigo}.{accion}"
                if not s.scalar(select(Permiso).where(Permiso.codigo==cod)):s.add(Permiso(modulo_id=m.id,nombre=f"{accion.title()} {m.nombre}",codigo=cod))
        s.flush()
        if not s.scalar(select(Clinica).where(Clinica.ruc=="20123456789")):
            c=Clinica(nombre_comercial="Clínica Dental Demo",razon_social="Clínica Dental Demo SAC",ruc="20123456789",correo="demo@clinica.com",telefono="999999999")
            s.add(c);s.flush();u=Usuario(clinica_id=c.id,nombres="Administrador",apellidos="Principal",correo="admin@clinica.com",nombre_usuario="admin",contrasena_hash=cifrar_contrasena("Admin12345*"));s.add(u);s.flush()
            admin=None
            for nombre in ROLES:
                r=Rol(clinica_id=c.id,nombre=nombre,es_sistema=True);s.add(r);s.flush()
                if nombre=="administrador":admin=r;s.add(UsuarioRol(usuario_id=u.id,rol_id=r.id))
            for m in modulos:s.add(ClinicaModulo(clinica_id=c.id,modulo_id=m.id,activo=m.codigo in ("configuracion","usuarios_roles_permisos")))
            for p in s.scalars(select(Permiso)):s.add(RolPermiso(rol_id=admin.id,permiso_id=p.id,puede_ver=True,puede_crear=True,puede_editar=True,puede_eliminar=True,puede_exportar=True))
        s.flush();sembrar_fase1(s);sembrar_fase2(s);s.commit()

def sembrar_fase1(s):
    modulos_fase1=["pacientes","historia_clinica","odontograma","agenda_citas","cotizaciones","planes_tratamiento"]
    acciones=("ver","crear","editar","eliminar","exportar")
    for codigo in modulos_fase1:
        m=s.scalar(select(Modulo).where(Modulo.codigo==codigo))
        if not m:continue
        for accion in acciones:
            cod=f"{codigo}.{accion}"
            if not s.scalar(select(Permiso).where(Permiso.codigo==cod)):s.add(Permiso(modulo_id=m.id,nombre=f"{accion.title()} {m.nombre}",codigo=cod))
    s.flush()
    demo=s.scalar(select(Clinica).where(Clinica.ruc=="20123456789"))
    if not demo:return
    for codigo in modulos_fase1:
        cm=s.scalar(select(ClinicaModulo).join(Modulo).where(ClinicaModulo.clinica_id==demo.id,Modulo.codigo==codigo))
        if cm:cm.activo=True
    sede=s.scalar(select(Sede).where(Sede.clinica_id==demo.id))
    if not sede:
        sede=Sede(clinica_id=demo.id,nombre="Sede Principal",direccion="Lima",cantidad_consultorios=2);s.add(sede);s.flush()
    if not s.scalar(select(Consultorio.id).where(Consultorio.clinica_id==demo.id)):
        s.add_all([Consultorio(clinica_id=demo.id,sede_id=sede.id,nombre="Consultorio 1"),Consultorio(clinica_id=demo.id,sede_id=sede.id,nombre="Consultorio 2")])
    if not s.scalar(select(TipoCita.id).where(TipoCita.clinica_id==demo.id)):
        s.add_all([TipoCita(clinica_id=demo.id,nombre="Evaluación",duracion_minutos=30,color="#0ea5e9"),TipoCita(clinica_id=demo.id,nombre="Tratamiento",duracion_minutos=60,color="#10b981")])
    matriz={"administrador":(True,True,True,True,True),"odontologo":(True,True,True,False,False),"recepcion":(True,True,True,True,False),"caja":(True,False,False,False,False)}
    for rol_nombre,flags in matriz.items():
        rol=s.scalar(select(Rol).where(Rol.clinica_id==demo.id,Rol.nombre==rol_nombre))
        if not rol:continue
        permitidos=modulos_fase1
        if rol_nombre=="recepcion":permitidos=["pacientes","agenda_citas","cotizaciones"]
        if rol_nombre=="caja":permitidos=["pacientes","cotizaciones","planes_tratamiento"]
        for codigo in permitidos:
            p=s.scalar(select(Permiso).where(Permiso.codigo==f"{codigo}.ver"))
            if p and not s.scalar(select(RolPermiso.id).where(RolPermiso.rol_id==rol.id,RolPermiso.permiso_id==p.id)):
                s.add(RolPermiso(rol_id=rol.id,permiso_id=p.id,puede_ver=flags[0],puede_crear=flags[1],puede_editar=flags[2],puede_eliminar=flags[3],puede_exportar=flags[4]))

def sembrar_fase2(s):
    codigos=["tratamientos_sesiones","pagos_caja","comprobantes_facturacion"]
    for codigo in codigos:
        m=s.scalar(select(Modulo).where(Modulo.codigo==codigo))
        if not m:continue
        for accion in ("ver","crear","editar","eliminar","exportar"):
            cod=f"{codigo}.{accion}"
            if not s.scalar(select(Permiso).where(Permiso.codigo==cod)):s.add(Permiso(modulo_id=m.id,nombre=f"{accion.title()} {m.nombre}",codigo=cod))
    s.flush();demo=s.scalar(select(Clinica).where(Clinica.ruc=="20123456789"))
    if not demo:return
    for codigo in codigos:
        cm=s.scalar(select(ClinicaModulo).join(Modulo).where(ClinicaModulo.clinica_id==demo.id,Modulo.codigo==codigo))
        if cm:cm.activo=True
    matriz={"administrador":{c:(1,1,1,1,1) for c in codigos},"odontologo":{"tratamientos_sesiones":(1,1,1,0,0),"pagos_caja":(1,0,0,0,0)},"recepcion":{"tratamientos_sesiones":(1,0,0,0,0),"pagos_caja":(1,1,0,0,0)},"caja":{"pagos_caja":(1,1,1,0,1),"comprobantes_facturacion":(1,1,1,0,1)}}
    for nombre,mods in matriz.items():
        rol=s.scalar(select(Rol).where(Rol.clinica_id==demo.id,Rol.nombre==nombre))
        if not rol:continue
        for codigo,flags in mods.items():
            p=s.scalar(select(Permiso).where(Permiso.codigo==f"{codigo}.ver"))
            if p and not s.scalar(select(RolPermiso.id).where(RolPermiso.rol_id==rol.id,RolPermiso.permiso_id==p.id)):s.add(RolPermiso(rol_id=rol.id,permiso_id=p.id,puede_ver=bool(flags[0]),puede_crear=bool(flags[1]),puede_editar=bool(flags[2]),puede_eliminar=bool(flags[3]),puede_exportar=bool(flags[4])))
if __name__=="__main__": ejecutar()
