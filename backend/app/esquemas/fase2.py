from datetime import date,datetime
from decimal import Decimal
from pydantic import BaseModel,Field,model_validator

class SesionCrear(BaseModel):
 sede_id:int;plan_tratamiento_id:int;detalle_plan_tratamiento_id:int;paciente_id:int;odontologo_id:int;cita_id:int|None=None;fecha_hora_inicio:datetime;fecha_hora_fin:datetime|None=None;procedimiento_realizado:str;pieza_dental:int|None=None;observaciones:str|None=None;indicaciones:str|None=None;proxima_sesion_fecha:datetime|None=None
class SesionDesdeCitaCrear(BaseModel): detalle_plan_tratamiento_id:int;pieza_dental:int|None=None;observaciones:str|None=None;indicaciones:str|None=None
class SesionActualizar(BaseModel): fecha_hora_inicio:datetime|None=None;fecha_hora_fin:datetime|None=None;procedimiento_realizado:str|None=None;pieza_dental:int|None=None;resultado:str|None=None;observaciones:str|None=None;indicaciones:str|None=None;proxima_sesion_fecha:datetime|None=None
class FinalizarSesion(BaseModel): resultado:str;observaciones:str|None=None;indicaciones:str|None=None;fecha_hora_fin:datetime|None=None;proxima_sesion_fecha:datetime|None=None
class MotivoOperacion(BaseModel): motivo:str=Field(min_length=3)
class ReprogramarSesion(BaseModel): fecha_hora_inicio:datetime;fecha_hora_fin:datetime|None=None;motivo:str=Field(min_length=3)
class InsumoCrear(BaseModel): nombre_insumo:str;cantidad:Decimal=Field(gt=0);unidad_medida:str;observaciones:str|None=None
class CuotaCrear(BaseModel): numero_cuota:int=Field(ge=1);descripcion:str|None=None;monto_cuota:Decimal=Field(gt=0);fecha_vencimiento:date
class CuentaCrear(BaseModel):
 sede_id:int;paciente_id:int;plan_tratamiento_id:int|None=None;cotizacion_id:int|None=None;descripcion:str;modalidad_cobro:str=Field(default="deuda_unica",pattern="^(deuda_unica|inicial_cuotas|cuotas_mensuales|por_procedimiento)$");monto_total:Decimal=Field(gt=0);fecha_vencimiento:date|None=None;cuotas:list[CuotaCrear]=[];confirmar_duplicado:bool=False
class CuentaActualizar(BaseModel): descripcion:str|None=None;fecha_vencimiento:date|None=None
class DetallePagoCrear(BaseModel):
 metodo_pago:str=Field(pattern="^(efectivo|yape|plin|transferencia|tarjeta_credito|tarjeta_debito|deposito|otro)$");monto:Decimal=Field(gt=0);numero_operacion:str|None=None;entidad_financiera:str|None=None;referencia:str|None=None;observaciones:str|None=None
 @model_validator(mode="after")
 def referencia_obligatoria(self):
  if self.metodo_pago in {"yape","plin","transferencia","tarjeta_credito","tarjeta_debito","deposito"} and not (self.numero_operacion or self.referencia):raise ValueError("El método exige número de operación o referencia registrada")
  return self
class AplicacionPagoCrear(BaseModel): cuenta_por_cobrar_id:int;cuota_cuenta_por_cobrar_id:int|None=None;monto_aplicado:Decimal=Field(gt=0)
class PagoCrear(BaseModel):
 sede_id:int;paciente_id:int;codigo_idempotencia:str=Field(min_length=8,max_length=80);monto_total:Decimal=Field(gt=0);vuelto:Decimal=Field(default=Decimal("0"),ge=0);observaciones:str|None=None;detalles:list[DetallePagoCrear]=Field(min_length=1);aplicaciones:list[AplicacionPagoCrear]=Field(min_length=1)
 @model_validator(mode="after")
 def sumas(self):
  if sum((x.monto for x in self.detalles),Decimal("0"))!=self.monto_total:raise ValueError("La suma de métodos debe ser igual al monto total")
  aplicado=sum((x.monto_aplicado for x in self.aplicaciones),Decimal("0"))
  if aplicado!=self.monto_total-self.vuelto:raise ValueError("La suma de aplicaciones debe ser igual al monto aplicado")
  return self
class DevolucionCrear(BaseModel): monto:Decimal=Field(gt=0);motivo:str=Field(min_length=3)
class AbrirCaja(BaseModel): sede_id:int;monto_inicial:Decimal=Field(default=Decimal("0"),ge=0);observaciones_apertura:str|None=None
class CerrarCaja(BaseModel): monto_final_declarado:Decimal=Field(ge=0);observaciones_cierre:str|None=None
class MovimientoManual(BaseModel): metodo_pago:str="efectivo";monto:Decimal=Field(gt=0);descripcion:str
class ComprobanteCrear(BaseModel): pago_id:int;concepto:str="Pago de tratamiento odontológico";observaciones:str|None=None
