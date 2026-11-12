import pytest
from pydantic import ValidationError
from app.esquemas.fase1 import DetallePlanCrear,PiezaPlanCrear,PlanCrear

def test_nombre_tratamiento_es_independiente_del_procedimiento():
 plan=PlanCrear(sede_id=1,paciente_id=1,odontologo_id=1,nombre_tratamiento="Rehabilitación integral")
 assert plan.nombre_tratamiento=="Rehabilitación integral"

def test_varias_piezas_con_roles_protesicos():
 detalle=DetallePlanCrear(procedimiento="Puente dental",tipo_alcance="varias_piezas",piezas=[PiezaPlanCrear(numero_pieza=14,rol_pieza="pilar"),PiezaPlanCrear(numero_pieza=15,rol_pieza="pontico"),PiezaPlanCrear(numero_pieza=16,rol_pieza="pilar")],cantidad_sesiones=4,costo_estimado="2300.00")
 assert [p.rol_pieza for p in detalle.piezas]==["pilar","pontico","pilar"]

def test_alcance_exige_sus_datos_clinicos():
 with pytest.raises(ValidationError):DetallePlanCrear(procedimiento="Endodoncia",tipo_alcance="pieza")
 with pytest.raises(ValidationError):DetallePlanCrear(procedimiento="Puente",tipo_alcance="varias_piezas")
 with pytest.raises(ValidationError):DetallePlanCrear(procedimiento="Periodoncia",tipo_alcance="cuadrante")

def test_rol_de_pieza_no_admite_texto_libre():
 with pytest.raises(ValidationError):PiezaPlanCrear(numero_pieza=14,rol_pieza="soporte improvisado")
