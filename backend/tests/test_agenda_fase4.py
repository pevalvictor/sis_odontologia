from datetime import datetime,timedelta,timezone
from test_fase1 import preparar,paciente

def escenario(cliente,sufijo="1"):
 h,sede=preparar(cliente,f'2088888888{sufijo}',f'fase4{sufijo}',['pacientes','agenda_citas','planes_tratamiento','tratamientos_sesiones']);p=paciente(cliente,h,f'7888000{sufijo}');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json();plan=cliente.post('/api/planes-tratamiento',headers=h,json={'sede_id':sede['id'],'paciente_id':p['id'],'odontologo_id':perfil['id'],'nombre_tratamiento':'Endodoncia'}).json();detalle=cliente.post(f"/api/planes-tratamiento/{plan['id']}/detalles",headers=h,json={'procedimiento':'Endodoncia','tipo_alcance':'pieza','pieza_dental':48,'piezas':[{'numero_pieza':48,'rol_pieza':'asociada'}],'cantidad_sesiones':2,'costo_estimado':'800.00'}).json();cliente.patch(f"/api/planes-tratamiento/{plan['id']}/aprobar",headers=h,json={});inicio=datetime.now(timezone.utc)+timedelta(days=2);cita=cliente.post('/api/citas',headers=h,json={'sede_id':sede['id'],'paciente_id':p['id'],'odontologo_id':perfil['id'],'plan_tratamiento_id':plan['id'],'tipo_cita':'procedimiento','fecha_hora_inicio':inicio.isoformat(),'fecha_hora_fin':(inicio+timedelta(hours=1)).isoformat(),'motivo':'Endodoncia programada'}).json();return h,plan,detalle,cita

def test_cita_confirmada_genera_una_sola_sesion_y_finaliza(cliente):
 h,plan,detalle,cita=escenario(cliente,'1');cliente.patch(f"/api/citas/{cita['id']}/confirmar",headers=h)
 r=cliente.post(f"/api/citas/{cita['id']}/sesion",headers=h,json={'detalle_plan_tratamiento_id':detalle['id'],'pieza_dental':48});assert r.status_code==201;sesion=r.json();assert sesion['cita_id']==cita['id'] and sesion['pieza_dental']==48
 assert cliente.post(f"/api/citas/{cita['id']}/sesion",headers=h,json={'detalle_plan_tratamiento_id':detalle['id'],'pieza_dental':48}).status_code==409
 assert cliente.patch(f"/api/sesiones-tratamiento/{sesion['id']}/finalizar",headers=h,json={'resultado':'Tratamiento realizado'}).status_code==200
 cita_final=cliente.get(f"/api/citas/{cita['id']}",headers=h).json();plan_final=cliente.get(f"/api/planes-tratamiento/{plan['id']}",headers=h).json();assert cita_final['estado']=='atendida' and plan_final['detalles'][0]['sesiones_completadas']==1

def test_no_genera_sesion_desde_cita_programada_o_cancelada(cliente):
 h,_,detalle,cita=escenario(cliente,'2');url=f"/api/citas/{cita['id']}/sesion";body={'detalle_plan_tratamiento_id':detalle['id'],'pieza_dental':48};assert cliente.post(url,headers=h,json=body).status_code==409;cliente.patch(f"/api/citas/{cita['id']}/cancelar",headers=h,json={'motivo':'Paciente cancela'});assert cliente.post(url,headers=h,json=body).status_code==409
