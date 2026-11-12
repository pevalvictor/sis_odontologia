from datetime import datetime,timezone,timedelta
import pytest
from pydantic import ValidationError
from app.esquemas.fase1 import CitaCrear

def base(**cambios):
 inicio=datetime(2026,7,3,9,tzinfo=timezone.utc);d=dict(sede_id=1,paciente_id=1,odontologo_id=1,tipo_cita="control",fecha_hora_inicio=inicio,fecha_hora_fin=inicio+timedelta(minutes=30),motivo="Control clínico")
 d.update(cambios);return d
def test_tipos_y_estados_admitidos():
 for tipo in ("evaluacion_inicial","control","procedimiento","urgencia","revision","ortodoncia","profilaxis","blanqueamiento","otro"):assert CitaCrear(**base(tipo_cita=tipo)).tipo_cita==tipo
 for estado in ("programada","confirmada","atendida","cancelada","no_asistio"):assert CitaCrear(**base(estado=estado)).estado==estado
def test_hora_fin_debe_ser_mayor():
 inicio=base()["fecha_hora_inicio"]
 with pytest.raises(ValidationError):CitaCrear(**base(fecha_hora_fin=inicio))
def test_tipo_y_estado_no_admiten_texto_libre():
 with pytest.raises(ValidationError):CitaCrear(**base(tipo_cita="implante_experimental"))
 with pytest.raises(ValidationError):CitaCrear(**base(estado="reprogramada"))
