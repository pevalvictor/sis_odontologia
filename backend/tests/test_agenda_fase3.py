from datetime import datetime,timedelta,timezone
from test_fase1 import preparar,paciente

def crear_plan(cliente,h,sede,paciente_id,odontologo_id,nombre="Ortodoncia"):
 plan=cliente.post('/api/planes-tratamiento',headers=h,json={'sede_id':sede['id'],'paciente_id':paciente_id,'odontologo_id':odontologo_id,'nombre_tratamiento':nombre}).json()
 assert cliente.patch(f"/api/planes-tratamiento/{plan['id']}/aprobar",headers=h,json={}).status_code==200
 return plan

def test_cita_independiente_y_cita_vinculada_a_plan(cliente):
 h,sede=preparar(cliente,'20999999991','agenda3',['pacientes','agenda_citas','planes_tratamiento']);p=paciente(cliente,h,'79990001');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json();plan=crear_plan(cliente,h,sede,p['id'],perfil['id']);inicio=datetime.now(timezone.utc)+timedelta(days=4)
 base={'sede_id':sede['id'],'paciente_id':p['id'],'odontologo_id':perfil['id'],'tipo_cita':'control','fecha_hora_inicio':inicio.isoformat(),'fecha_hora_fin':(inicio+timedelta(minutes=30)).isoformat(),'motivo':'Control del tratamiento'}
 independiente=cliente.post('/api/citas',headers=h,json=base);assert independiente.status_code==201 and independiente.json()['plan_tratamiento_id'] is None
 vinculada=cliente.post('/api/citas',headers=h,json={**base,'plan_tratamiento_id':plan['id'],'fecha_hora_inicio':(inicio+timedelta(hours=1)).isoformat(),'fecha_hora_fin':(inicio+timedelta(hours=1,minutes=30)).isoformat()});assert vinculada.status_code==201 and vinculada.json()['tratamiento_relacionado']=='Ortodoncia'
 assert len(cliente.get(f"/api/citas/plan/{plan['id']}",headers=h).json())==1

def test_rechaza_plan_de_otro_paciente(cliente):
 h,sede=preparar(cliente,'20999999992','agenda4',['pacientes','agenda_citas','planes_tratamiento']);p1=paciente(cliente,h,'79990002');p2=paciente(cliente,h,'79990003');perfil=cliente.get('/api/autenticacion/mi-perfil',headers=h).json();plan=crear_plan(cliente,h,sede,p1['id'],perfil['id']);inicio=datetime.now(timezone.utc)+timedelta(days=5)
 r=cliente.post('/api/citas',headers=h,json={'sede_id':sede['id'],'paciente_id':p2['id'],'odontologo_id':perfil['id'],'plan_tratamiento_id':plan['id'],'tipo_cita':'control','fecha_hora_inicio':inicio.isoformat(),'fecha_hora_fin':(inicio+timedelta(minutes=30)).isoformat(),'motivo':'Plan incorrecto'})
 assert r.status_code==422
