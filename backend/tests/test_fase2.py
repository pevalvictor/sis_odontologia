from datetime import date,datetime,timedelta,timezone
from sqlalchemy import select
from conftest import SesionPrueba
from app.modelos import Usuario,Modulo,ClinicaModulo,DetallePlanTratamiento,PlanTratamiento,MovimientoCaja,Pago,ComprobanteInterno

def preparar(c,ruc='20888888888',usuario='fase2'):
 c.post('/api/autenticacion/registro-inicial',json={'nombre_comercial':'Clínica Fase 2','ruc':ruc,'correo_clinica':f'{usuario}@example.com','nombres_administrador':'Admin','apellidos_administrador':'Fase2','correo_administrador':f'admin{usuario}@example.com','nombre_usuario':usuario,'contrasena':'Segura123*'});t=c.post('/api/autenticacion/iniciar-sesion',json={'identificador':usuario,'contrasena':'Segura123*','ruc':ruc}).json()['access_token'];h={'Authorization':f'Bearer {t}'}
 with SesionPrueba() as s:
  uid=s.scalar(select(Usuario.id).where(Usuario.nombre_usuario==usuario));u=s.get(Usuario,uid)
  for codigo in ['pacientes','planes_tratamiento','tratamientos_sesiones','pagos_caja','comprobantes_facturacion']:
   cm=s.scalar(select(ClinicaModulo).join(Modulo).where(ClinicaModulo.clinica_id==u.clinica_id,Modulo.codigo==codigo));cm.activo=True
  s.commit()
 sede=c.post('/api/sedes',headers=h,json={'nombre':'Principal','direccion':'Lima'}).json();p=c.post('/api/pacientes',headers=h,json={'tipo_documento':'DNI','numero_documento':ruc[-8:],'nombres':'Paciente','apellidos':'Finanzas','fecha_nacimiento':'1990-01-01'}).json();perfil=c.get('/api/autenticacion/mi-perfil',headers=h).json();return h,sede,p,perfil
def plan_aprobado(c,h,sede,p,u,costo='300.00'):
 plan=c.post('/api/planes-tratamiento',headers=h,json={'sede_id':sede['id'],'paciente_id':p['id'],'odontologo_id':u['id'],'diagnostico_principal':'Tratamiento integral'}).json();det=c.post(f"/api/planes-tratamiento/{plan['id']}/detalles",headers=h,json={'procedimiento':'Restauración','cantidad_sesiones':2,'costo_estimado':costo}).json();c.patch(f"/api/planes-tratamiento/{plan['id']}/aprobar",headers=h,json={});return plan,det
def cuenta_cuotas(c,h,sede,p,plan,total='300.00'):
 return c.post('/api/cuentas-por-cobrar',headers=h,json={'sede_id':sede['id'],'paciente_id':p['id'],'plan_tratamiento_id':plan['id'],'descripcion':'Plan financiado','modalidad_cobro':'cuotas_mensuales','monto_total':total,'cuotas':[{'numero_cuota':1,'monto_cuota':'150.00','fecha_vencimiento':str(date.today())},{'numero_cuota':2,'monto_cuota':'150.00','fecha_vencimiento':str(date.today()+timedelta(days=30))}]}).json()
def abrir(c,h,sede):return c.post('/api/cajas/abrir',headers=h,json={'sede_id':sede['id'],'monto_inicial':'100.00'}).json()

def test_sesion_actualiza_avance_y_plan_cancelado_rechaza(cliente):
 h,sede,p,u=preparar(cliente);plan,det=plan_aprobado(cliente,h,sede,p,u);inicio=datetime.now(timezone.utc)
 ses=cliente.post('/api/sesiones-tratamiento',headers=h,json={'sede_id':sede['id'],'plan_tratamiento_id':plan['id'],'detalle_plan_tratamiento_id':det['id'],'paciente_id':p['id'],'odontologo_id':u['id'],'fecha_hora_inicio':inicio.isoformat(),'procedimiento_realizado':'Restauración'}).json();assert cliente.patch(f"/api/sesiones-tratamiento/{ses['id']}/finalizar",headers=h,json={'resultado':'Satisfactorio'}).status_code==200
 detalle=cliente.get(f"/api/planes-tratamiento/{plan['id']}",headers=h).json()['detalles'][0];assert detalle['sesiones_completadas']==1
 cliente.patch(f"/api/planes-tratamiento/{plan['id']}/estado",headers=h,json={'estado':'cancelado'});assert cliente.post('/api/sesiones-tratamiento',headers=h,json={'sede_id':sede['id'],'plan_tratamiento_id':plan['id'],'detalle_plan_tratamiento_id':det['id'],'paciente_id':p['id'],'odontologo_id':u['id'],'fecha_hora_inicio':inicio.isoformat(),'procedimiento_realizado':'Otra'}).status_code==409

def test_pago_exige_caja_distribuye_cuotas_e_idempotencia(cliente):
 h,sede,p,u=preparar(cliente,'20999999991','pagos');plan,_=plan_aprobado(cliente,h,sede,p,u);cuenta=cuenta_cuotas(cliente,h,sede,p,plan);detalle=cliente.get(f"/api/cuentas-por-cobrar/{cuenta['id']}",headers=h).json();q1,q2=detalle['cuotas'];body={'sede_id':sede['id'],'paciente_id':p['id'],'codigo_idempotencia':'pago-prueba-0001','monto_total':'300.00','detalles':[{'metodo_pago':'yape','monto':'100.00','numero_operacion':'YAPE-001'},{'metodo_pago':'efectivo','monto':'200.00'}],'aplicaciones':[{'cuenta_por_cobrar_id':cuenta['id'],'cuota_cuenta_por_cobrar_id':q1['id'],'monto_aplicado':'150.00'},{'cuenta_por_cobrar_id':cuenta['id'],'cuota_cuenta_por_cobrar_id':q2['id'],'monto_aplicado':'150.00'}]}
 assert cliente.post('/api/pagos',headers=h,json=body).status_code==409;abrir(cliente,h,sede);r=cliente.post('/api/pagos',headers=h,json=body);assert r.status_code==201;pid=r.json()['id'];assert cliente.post('/api/pagos',headers=h,json=body).json()['id']==pid
 estado=cliente.get(f"/api/cuentas-por-cobrar/{cuenta['id']}/estado-cuenta",headers=h).json();assert estado['saldo_pendiente']==0 and estado['estado']=='pagada';pago=cliente.get(f'/api/pagos/{pid}',headers=h).json();assert sum(x['monto_aplicado'] for x in pago['aplicaciones'])==300
 movs=cliente.get(f"/api/cajas/{r.json()['caja_id']}/movimientos",headers=h).json();assert sum(x['monto'] for x in movs if x['metodo_pago']=='efectivo')==200 and sum(x['monto'] for x in movs if x['metodo_pago']=='yape')==100

def test_validaciones_anulacion_y_fotografia_comprobante(cliente):
 h,sede,p,u=preparar(cliente,'20999999992','recibo');plan,_=plan_aprobado(cliente,h,sede,p,u);cuenta=cuenta_cuotas(cliente,h,sede,p,plan);q=cliente.get(f"/api/cuentas-por-cobrar/{cuenta['id']}",headers=h).json()['cuotas'][0];abrir(cliente,h,sede)
 malo={'sede_id':sede['id'],'paciente_id':p['id'],'codigo_idempotencia':'pago-malo-0001','monto_total':'170.00','detalles':[{'metodo_pago':'efectivo','monto':'160.00'}],'aplicaciones':[{'cuenta_por_cobrar_id':cuenta['id'],'cuota_cuenta_por_cobrar_id':q['id'],'monto_aplicado':'150.00'}]};assert cliente.post('/api/pagos',headers=h,json=malo).status_code==422
 body={**malo,'codigo_idempotencia':'pago-recibo-0001','monto_total':'150.00','detalles':[{'metodo_pago':'yape','monto':'100.00','referencia':'REF-1'},{'metodo_pago':'efectivo','monto':'50.00'}]};pago=cliente.post('/api/pagos',headers=h,json=body).json();comp=cliente.post('/api/comprobantes-internos',headers=h,json={'pago_id':pago['id']}).json();foto=cliente.get(f"/api/comprobantes-internos/{comp['id']}",headers=h).json();assert foto['fotografia_paciente']['nombres']=='Paciente' and len(foto['fotografia_metodos_pago'])==2
 assert cliente.patch(f"/api/pagos/{pago['id']}/anular",headers=h,json={'motivo':'Error de registro'}).status_code==200;estado=cliente.get(f"/api/cuentas-por-cobrar/{cuenta['id']}/estado-cuenta",headers=h).json();assert estado['saldo_pendiente']==300

def test_aislamiento_cuentas(cliente):
 h1,s1,p1,u1=preparar(cliente,'20999999993','uno2');plan,_=plan_aprobado(cliente,h1,s1,p1,u1);cuenta=cuenta_cuotas(cliente,h1,s1,p1,plan);h2,_,_,_=preparar(cliente,'20999999994','dos2');assert cliente.get(f"/api/cuentas-por-cobrar/{cuenta['id']}",headers=h2).status_code==404
