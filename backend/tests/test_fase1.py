from datetime import datetime, timedelta, timezone, date
from sqlalchemy import select
from app.core.seguridad import cifrar_contrasena
from app.modelos import ClinicaModulo, Modulo, Sede, Usuario, Rol, UsuarioRol, BitacoraAuditoria
from conftest import SesionPrueba

def registrar(c,ruc,usuario):
    return c.post('/api/autenticacion/registro-inicial',json={'nombre_comercial':f'Clínica {usuario}','ruc':ruc,'correo_clinica':f'{usuario}@example.com','nombres_administrador':'Admin','apellidos_administrador':usuario,'correo_administrador':f'admin{usuario}@example.com','nombre_usuario':usuario,'contrasena':'Segura123*'})
def iniciar(c,ruc,usuario):return c.post('/api/autenticacion/iniciar-sesion',json={'identificador':usuario,'contrasena':'Segura123*','ruc':ruc}).json()['access_token']
def preparar(c,ruc,usuario,modulos):
    registrar(c,ruc,usuario);token=iniciar(c,ruc,usuario);h={'Authorization':f'Bearer {token}'}
    with SesionPrueba() as s:
        clinica=s.scalar(select(Usuario).where(Usuario.nombre_usuario==usuario)).clinica_id
        for codigo in modulos:
            cm=s.scalar(select(ClinicaModulo).join(Modulo).where(ClinicaModulo.clinica_id==clinica,Modulo.codigo==codigo));cm.activo=True
        s.commit()
    sede=c.post('/api/sedes',headers=h,json={'nombre':'Principal','direccion':'Lima'}).json();return h,sede
def paciente(c,h,doc):return c.post('/api/pacientes',headers=h,json={'tipo_documento':'DNI','numero_documento':doc,'nombres':'Paciente','apellidos':'Prueba','fecha_nacimiento':'1990-01-01'}).json()

def test_aislamiento_pacientes_y_acceso_cruzado(cliente):
    h1,_=preparar(cliente,'20111111111','uno',['pacientes']);h2,_=preparar(cliente,'20222222222','dos',['pacientes']);p=paciente(cliente,h1,'70000001')
    assert cliente.get('/api/pacientes',headers=h2).json()['total']==0
    assert cliente.get(f"/api/pacientes/{p['id']}",headers=h2).status_code==404

def test_no_permite_citas_superpuestas_y_audita(cliente):
    h,sede=preparar(cliente,'20333333333','agenda',['pacientes','agenda_citas']);p=paciente(cliente,h,'70000002');consultorio=cliente.post(f"/api/consultorios?sede_id={sede['id']}&nombre=Uno",headers=h).json()
    perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json();ini=datetime.now(timezone.utc)+timedelta(days=1);fin=ini+timedelta(hours=1)
    base={'sede_id':sede['id'],'consultorio_id':consultorio['id'],'paciente_id':p['id'],'odontologo_id':perfil['id'],'fecha_hora_inicio':ini.isoformat(),'fecha_hora_fin':fin.isoformat(),'motivo':'Evaluación'}
    assert cliente.post('/api/citas',headers=h,json=base).status_code==201
    assert cliente.post('/api/citas',headers=h,json={**base,'consultorio_id':None}).status_code==409
    with SesionPrueba() as s:
        admin=s.scalar(select(Usuario).where(Usuario.id==perfil['id']));otro=Usuario(clinica_id=admin.clinica_id,nombres='Otro',apellidos='Odontólogo',correo='otro@example.com',nombre_usuario='otro',contrasena_hash=cifrar_contrasena('Segura123*'));s.add(otro);s.commit();otro_id=otro.id
    assert cliente.post('/api/citas',headers=h,json={**base,'odontologo_id':otro_id}).status_code==409
    with SesionPrueba() as s:assert s.scalar(select(BitacoraAuditoria.id).where(BitacoraAuditoria.accion=='crear'))

def test_cotizacion_calculo_conversion_y_bloqueo(cliente):
    h,sede=preparar(cliente,'20444444444','comercial',['pacientes','cotizaciones','planes_tratamiento']);p=paciente(cliente,h,'70000003');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json()
    cot=cliente.post('/api/cotizaciones',headers=h,json={'sede_id':sede['id'],'paciente_id':p['id'],'odontologo_id':perfil['id'],'fecha_vigencia':str(date.today()+timedelta(days=15)),'detalles':[{'procedimiento':'Limpieza','cantidad':2,'precio_unitario':'100.00','descuento_porcentaje':'10'}]}).json()
    assert cot['subtotal']==200 and cot['descuento_total']==20 and cot['total_estimado']==180
    assert cliente.patch(f"/api/cotizaciones/{cot['id']}/estado",headers=h,json={'estado':'aceptada'}).status_code==200
    assert cliente.post(f"/api/cotizaciones/{cot['id']}/convertir-plan",headers=h).status_code==201
    assert cliente.put(f"/api/cotizaciones/{cot['id']}",headers=h,json={'observaciones':'No debe cambiar'}).status_code==409

def test_recepcion_no_edita_historia(cliente):
    h,sede=preparar(cliente,'20555555555','clinica',['pacientes','historia_clinica']);p=paciente(cliente,h,'70000004')
    with SesionPrueba() as s:
        admin=s.scalar(select(Usuario).where(Usuario.nombre_usuario=='clinica'));rol=s.scalar(select(Rol).where(Rol.clinica_id==admin.clinica_id,Rol.nombre=='recepcion'));u=Usuario(clinica_id=admin.clinica_id,nombres='Rosa',apellidos='Recepción',correo='recepcion@example.com',nombre_usuario='recepcion',contrasena_hash=cifrar_contrasena('Segura123*'));s.add(u);s.flush();s.add(UsuarioRol(usuario_id=u.id,rol_id=rol.id));s.commit()
    tr=iniciar(cliente,'20555555555','recepcion');hr={'Authorization':f'Bearer {tr}'}
    assert cliente.post(f"/api/historias-clinicas/paciente/{p['id']}",headers=hr).status_code==403

def test_odontograma_actualiza_resumen_y_conserva_historial(cliente):
    h,_=preparar(cliente,'20666666666','odonto',['pacientes','odontograma']);p=paciente(cliente,h,'70000005');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json()
    o=cliente.post(f"/api/odontogramas/paciente/{p['id']}",headers=h,json={'odontologo_id':perfil['id']}).json()
    base={'superficie_dental':'oclusal','diagnostico':'Caries oclusal','tratamiento_indicado':'Obturación','condicion':'caries','estado_tratamiento':'pendiente'}
    assert cliente.post(f"/api/odontogramas/{o['id']}/piezas/16/hallazgos",headers=h,json=base).status_code==201
    assert cliente.post(f"/api/odontogramas/{o['id']}/piezas/16/hallazgos",headers=h,json={**base,'diagnostico':'Control','condicion':'obturado','estado_tratamiento':'finalizado'}).status_code==201
    piezas=cliente.get(f"/api/odontogramas/{o['id']}/piezas",headers=h).json();pieza=next(x for x in piezas if x['numero_pieza']==16)
    historial=cliente.get(f"/api/odontogramas/{o['id']}/piezas/16/historial",headers=h).json()
    assert pieza['condicion']=='obturado' and pieza['estado_tratamiento']=='finalizado' and len(historial)==2

def test_denticion_temporal_mixta_y_sucesor_fdi(cliente):
    h,_=preparar(cliente,'20777777777','pediatria',['pacientes','odontograma']);p=paciente(cliente,h,'70000006');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json()
    temporal=cliente.post(f"/api/odontogramas/paciente/{p['id']}",headers=h,json={'odontologo_id':perfil['id'],'tipo_denticion':'temporal'}).json();pt=cliente.get(f"/api/odontogramas/{temporal['id']}/piezas",headers=h).json()
    assert temporal['tipo_denticion']=='temporal' and len(pt)==20 and all(x['tipo_pieza']=='temporal' for x in pt)
    assert cliente.patch(f"/api/odontogramas/{temporal['id']}/piezas/51/estado-general",headers=h,json={'numero_pieza_sucesora':21}).status_code==422
    assert cliente.patch(f"/api/odontogramas/{temporal['id']}/piezas/51/estado-general",headers=h,json={'numero_pieza_sucesora':11,'estado_pieza':'perdida_prematura','perdida_prematura':True}).status_code==200
    mixta=cliente.post(f"/api/odontogramas/paciente/{p['id']}",headers=h,json={'odontologo_id':perfil['id'],'tipo_denticion':'mixta'}).json();pm=cliente.get(f"/api/odontogramas/{mixta['id']}/piezas",headers=h).json()
    assert len(pm)==52 and sum(x['estado_erupcion']=='no_erupcionado' for x in pm)==32
