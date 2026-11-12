"""Seis citas demostrativas. Ejecutar: python -m app.db.semillas_demo_agenda"""
from datetime import datetime,date,time,timezone,timedelta
from sqlalchemy import select
from app.db.sesion import SesionLocal
from app.modelos import Clinica,Sede,Usuario,Paciente,Cita
def ejecutar():
 with SesionLocal() as s:
  clinica=s.scalar(select(Clinica).order_by(Clinica.id));sede=s.scalar(select(Sede).where(Sede.clinica_id==clinica.id));odontologo=s.scalar(select(Usuario).where(Usuario.clinica_id==clinica.id).order_by(Usuario.id));pacientes=list(s.scalars(select(Paciente).where(Paciente.clinica_id==clinica.id).limit(6)))
  if not pacientes:print("Primero cree pacientes");return
  base=datetime.combine(date.today(),time(8),tzinfo=timezone.utc);casos=(("evaluacion_inicial","Evaluación odontológica","programada"),("control","Control postoperatorio","confirmada"),("procedimiento","Restauración dental","atendida"),("urgencia","Dolor dental agudo","cancelada"),("revision","Revisión clínica","no_asistio"),("profilaxis","Limpieza dental","programada"))
  for i,(tipo,motivo,estado) in enumerate(casos):
   inicio=base+timedelta(hours=i)
   if s.scalar(select(Cita.id).where(Cita.clinica_id==clinica.id,Cita.motivo==f"DEMO AGENDA · {motivo}")):continue
   s.add(Cita(clinica_id=clinica.id,sede_id=sede.id,paciente_id=pacientes[i%len(pacientes)].id,odontologo_id=odontologo.id,tipo_cita=tipo,fecha_hora_inicio=inicio,fecha_hora_fin=inicio+timedelta(minutes=30),motivo=f"DEMO AGENDA · {motivo}",observaciones="Dato demostrativo de Agenda Fase 1",estado=estado,motivo_cambio="Demostración" if estado=="cancelada" else None))
  s.commit();print("Seis citas demostrativas creadas")
if __name__=="__main__":ejecutar()
