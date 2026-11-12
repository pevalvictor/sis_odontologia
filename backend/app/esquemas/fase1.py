from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, model_validator

class PacienteCrear(BaseModel):
    sede_id:int|None=None;tipo_documento:str|None=None;numero_documento:str|None=None;es_temporal:bool=False;nombres:str=Field(min_length=2);apellidos:str=Field(min_length=2);fecha_nacimiento:date|None=None;sexo:str|None=None;telefono:str|None=None;correo:EmailStr|None=None;direccion:str|None=None;ocupacion:str|None=None;estado_civil:str|None=None;grupo_sanguineo:str|None=None;seguro_medico:str|None=None;contacto_emergencia_nombre:str|None=None;contacto_emergencia_telefono:str|None=None;observaciones:str|None=None
    @model_validator(mode="after")
    def validar(self):
        if not self.es_temporal and not self.numero_documento: raise ValueError("El documento es obligatorio salvo para pacientes temporales")
        if self.fecha_nacimiento and self.fecha_nacimiento>date.today(): raise ValueError("La fecha de nacimiento no puede ser futura")
        return self
class PacienteActualizar(BaseModel):
    sede_id:int|None=None;tipo_documento:str|None=None;numero_documento:str|None=None;es_temporal:bool|None=None;nombres:str|None=None;apellidos:str|None=None;fecha_nacimiento:date|None=None;sexo:str|None=None;telefono:str|None=None;correo:EmailStr|None=None;direccion:str|None=None;ocupacion:str|None=None;estado_civil:str|None=None;grupo_sanguineo:str|None=None;seguro_medico:str|None=None;contacto_emergencia_nombre:str|None=None;contacto_emergencia_telefono:str|None=None;observaciones:str|None=None
class AntecedenteCrear(BaseModel): tipo_antecedente:str;descripcion:str
class AlergiaCrear(BaseModel): nombre:str;descripcion:str|None=None;nivel_riesgo:str=Field(default="medio",pattern="^(bajo|medio|alto|critico)$")
class EstadoPaciente(BaseModel): estado:bool
class ConsultaCrear(BaseModel): paciente_id:int;sede_id:int;odontologo_id:int;fecha_consulta:datetime|None=None;motivo_consulta:str;sintomas:str|None=None;diagnostico:str|None=None;procedimiento_realizado:str|None=None;observaciones:str|None=None;indicaciones:str|None=None;proxima_recomendacion:str|None=None
class ConsultaActualizar(BaseModel): motivo_consulta:str|None=None;sintomas:str|None=None;diagnostico:str|None=None;procedimiento_realizado:str|None=None;observaciones:str|None=None;indicaciones:str|None=None;proxima_recomendacion:str|None=None
class EvolucionCrear(BaseModel): descripcion:str
class AnularConsulta(BaseModel): motivo:str=Field(min_length=5)
class HallazgoCrear(BaseModel): superficie_dental:str=Field(pattern="^(oclusal|mesial|distal|vestibular|lingual|palatina)$");diagnostico:str;tratamiento_indicado:str|None=None;estado:str="pendiente";observaciones:str|None=None;consulta_clinica_id:int|None=None;detalle_plan_tratamiento_id:int|None=None;condicion:str|None=Field(default=None,pattern="^(sano|caries|obturado|endodoncia|extraccion|ortodoncia|corona|implante|protesis|periodontal|ausente|retenido|sin_erupcionar)$");estado_tratamiento:str|None=Field(default=None,pattern="^(pendiente|en_tratamiento|finalizado|suspendido|cancelado)$");tipo_pieza:str|None=Field(default=None,pattern="^(temporal|permanente)$");estado_erupcion:str|None=Field(default=None,pattern="^(no_erupcionado|en_erupcion|erupcionado|retenido)$");estado_pieza:str|None=Field(default=None,pattern="^(presente|ausente|exfoliacion_fisiologica|perdida_prematura|extraido)$");perdida_prematura:bool|None=None;numero_pieza_sucesora:int|None=None
class HallazgoActualizar(BaseModel): tratamiento_indicado:str|None=None;estado:str|None=None;observaciones:str|None=None
class OdontogramaCrear(BaseModel): odontologo_id:int;observaciones_generales:str|None=None;tipo_denticion:str=Field(default="permanente",pattern="^(permanente|temporal|mixta)$")
class OdontogramaActualizar(BaseModel): observaciones_generales:str|None=None;estado:str|None=None
class PiezaEstadoActualizar(BaseModel):
    tipo_pieza:str|None=Field(default=None,pattern="^(temporal|permanente)$");estado_erupcion:str|None=Field(default=None,pattern="^(no_erupcionado|en_erupcion|erupcionado|retenido)$");estado_pieza:str|None=Field(default=None,pattern="^(presente|ausente|exfoliacion_fisiologica|perdida_prematura|extraido)$");perdida_prematura:bool|None=None;numero_pieza_sucesora:int|None=None
class CitaCrear(BaseModel):
    sede_id:int;consultorio_id:int|None=None;paciente_id:int;odontologo_id:int;plan_tratamiento_id:int|None=None;tipo_cita_id:int|None=None;tipo_cita:str=Field(default="otro",pattern="^(evaluacion_inicial|control|procedimiento|urgencia|revision|ortodoncia|profilaxis|blanqueamiento|otro)$");fecha_hora_inicio:datetime;fecha_hora_fin:datetime;motivo:str=Field(min_length=3);observaciones:str|None=None;estado:str=Field(default="programada",pattern="^(programada|confirmada|en_atencion|atendida|cancelada|no_asistio)$")
    @model_validator(mode="after")
    def fechas(self):
        if self.fecha_hora_fin<=self.fecha_hora_inicio:raise ValueError("La fecha de fin debe ser posterior al inicio")
        return self
class CitaActualizar(CitaCrear): pass
class MotivoCambio(BaseModel): motivo:str=Field(min_length=3)
class ReprogramarCita(MotivoCambio): fecha_hora_inicio:datetime;fecha_hora_fin:datetime
class PlantillaRecordatorioCrear(BaseModel):
    nombre:str=Field(min_length=3);canal:str=Field(default="interno",pattern="^(interno|whatsapp|sms|email)$");asunto:str|None=None;contenido:str=Field(min_length=5);variables:str|None=None;activo:bool=True
class PlantillaRecordatorioActualizar(BaseModel):
    nombre:str|None=None;canal:str|None=Field(default=None,pattern="^(interno|whatsapp|sms|email)$");asunto:str|None=None;contenido:str|None=None;variables:str|None=None;activo:bool|None=None
class RecordatorioCitaCrear(BaseModel):
    plantilla_id:int|None=None;canal:str=Field(default="interno",pattern="^(interno|whatsapp|sms|email)$");destinatario:str|None=None;mensaje:str|None=None;estado:str=Field(default="pendiente",pattern="^(pendiente|enviado|fallido|cancelado)$");fecha_programada:datetime|None=None;observaciones:str|None=None
class MarcarRecordatorioEnviado(BaseModel): observaciones:str|None=None
class DetalleCotizacionCrear(BaseModel): procedimiento:str;descripcion:str|None=None;pieza_dental:int|None=None;cantidad:int=Field(default=1,ge=1);precio_unitario:Decimal=Field(ge=0);descuento_porcentaje:Decimal=Field(default=0,ge=0,le=100);orden:int=0
class CotizacionCrear(BaseModel): sede_id:int;paciente_id:int;odontologo_id:int;fecha_vigencia:date;diagnostico_resumen:str|None=None;observaciones:str|None=None;condiciones:str|None=None;pago_inicial_propuesto:Decimal=Field(default=Decimal("0"),ge=0);numero_cuotas_propuesto:int=Field(default=0,ge=0);detalles:list[DetalleCotizacionCrear]=[]
class CotizacionActualizar(BaseModel): fecha_vigencia:date|None=None;diagnostico_resumen:str|None=None;observaciones:str|None=None;condiciones:str|None=None;pago_inicial_propuesto:Decimal|None=Field(default=None,ge=0);numero_cuotas_propuesto:int|None=Field(default=None,ge=0)
class EstadoCotizacion(BaseModel): estado:str=Field(pattern="^(borrador|entregada|en_evaluacion|aceptada|rechazada|vencida|convertida)$")
class PlanCrear(BaseModel): sede_id:int;paciente_id:int;odontologo_id:int;nombre_tratamiento:str|None=None;diagnostico_principal:str|None=None;fecha_inicio_estimada:date|None=None;fecha_fin_estimada:date|None=None;duracion_estimada_meses:int|None=None
class PiezaPlanCrear(BaseModel): numero_pieza:int;rol_pieza:str=Field(default="asociada",pattern="^(pilar|pontico|asociada)$")
class DetallePlanCrear(BaseModel):
 procedimiento:str;descripcion:str|None=None;pieza_dental:int|None=None;tipo_alcance:str=Field(default="general",pattern="^(pieza|varias_piezas|cuadrante|arcada_superior|arcada_inferior|ambas_arcadas|general)$");cuadrante:str|None=Field(default=None,pattern="^(cuadrante_[1-4]|superior_derecho|superior_izquierdo|inferior_derecho|inferior_izquierdo)$");piezas:list[PiezaPlanCrear]=[];cantidad_sesiones:int=Field(default=1,ge=1);sesiones_completadas:int=Field(default=0,ge=0);fecha_estimada:date|None=None;costo_estimado:Decimal=Field(default=0,ge=0);estado:str="pendiente";orden:int=0
 @model_validator(mode="after")
 def alcance_valido(self):
  if self.tipo_alcance=="pieza" and not (self.pieza_dental or len(self.piezas)==1):raise ValueError("El alcance pieza exige una pieza")
  if self.tipo_alcance=="varias_piezas" and not self.piezas:raise ValueError("Debe seleccionar una o más piezas")
  if self.tipo_alcance=="cuadrante" and not self.cuadrante:raise ValueError("Debe seleccionar el cuadrante")
  return self
class PlanActualizar(BaseModel): nombre_tratamiento:str|None=None;diagnostico_principal:str|None=None;fecha_inicio_estimada:date|None=None;fecha_fin_estimada:date|None=None;duracion_estimada_meses:int|None=None
class EstadoPlan(BaseModel): estado:str=Field(pattern="^(propuesto|aprobado|activo|suspendido|finalizado|cancelado)$")
class AprobarPlan(BaseModel): observacion:str|None=None
