"""Planes clínicos demostrativos de alcance. Ejecutar: python -m app.db.semillas_demo_planes_clinicos"""
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from app.db.sesion import SesionLocal
from app.modelos import Clinica,Sede,Usuario,Paciente,PlanTratamiento,DetallePlanTratamiento,DetallePlanPieza

CASOS=(
 ("Victor","Pérez Valqui","DEMO-PLAN-01","Ortodoncia con brackets","Maloclusión dental","Brackets","ambas_arcadas",[],18,"4500"),
 ("María","Gómez","DEMO-PLAN-02","Blanqueamiento dental","Discromía dental","Blanqueamiento","general",[],2,"650"),
 ("Carlos","Ruiz","DEMO-PLAN-03","Endodoncia pieza 48","Pulpitis irreversible en pieza 48","Endodoncia","pieza",[(48,"asociada")],3,"800"),
 ("Ana","Torres","DEMO-PLAN-04","Puente dental 14-16","Ausencia de pieza 15","Puente dental","varias_piezas",[(14,"pilar"),(15,"pontico"),(16,"pilar")],4,"2300"),
)
def ejecutar():
 with SesionLocal() as s:
  clinica=s.scalar(select(Clinica).order_by(Clinica.id));sede=s.scalar(select(Sede).where(Sede.clinica_id==clinica.id));odontologo=s.scalar(select(Usuario).where(Usuario.clinica_id==clinica.id).order_by(Usuario.id))
  for nombres,apellidos,documento,nombre,diagnostico,procedimiento,alcance,piezas,sesiones,costo in CASOS:
   paciente=s.scalar(select(Paciente).where(Paciente.clinica_id==clinica.id,Paciente.numero_documento==documento))
   if not paciente:paciente=Paciente(clinica_id=clinica.id,sede_id=sede.id,tipo_documento="DNI",numero_documento=documento,nombres=nombres,apellidos=apellidos,fecha_nacimiento=date(1990,1,1));s.add(paciente);s.flush()
   numero=f"PLAN-{documento}"
   if s.scalar(select(PlanTratamiento.id).where(PlanTratamiento.clinica_id==clinica.id,PlanTratamiento.numero_plan==numero)):continue
   plan=PlanTratamiento(clinica_id=clinica.id,sede_id=sede.id,paciente_id=paciente.id,odontologo_id=odontologo.id,numero_plan=numero,nombre_tratamiento=nombre,diagnostico_principal=diagnostico,costo_total_estimado=Decimal(costo),avance_porcentaje=0,estado="aprobado");s.add(plan);s.flush()
   detalle=DetallePlanTratamiento(plan_tratamiento_id=plan.id,procedimiento=procedimiento,tipo_alcance=alcance,pieza_dental=piezas[0][0] if alcance=="pieza" else None,cantidad_sesiones=sesiones,sesiones_completadas=0,costo_estimado=Decimal(costo),estado="pendiente",orden=1);s.add(detalle);s.flush()
   for numero_pieza,rol in piezas:s.add(DetallePlanPieza(detalle_plan_tratamiento_id=detalle.id,numero_pieza=numero_pieza,rol_pieza=rol))
  s.commit();print("Planes clínicos demostrativos creados")
if __name__=="__main__":ejecutar()
