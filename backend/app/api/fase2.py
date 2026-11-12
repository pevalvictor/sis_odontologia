from datetime import date,datetime,timezone
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.db.sesion import obtener_sesion
from app.dependencias.seguridad import exigir_permiso
from app.esquemas.fase2 import *
from app.modelos import *
from app.servicios.auditoria import auditar
from app.api.fase1 import dic,propio,paciente_propio,recalcular_plan,pdf_basico

router=APIRouter(prefix="/api")
def cuenta_propia(s,id_,clinica):return propio(s,CuentaPorCobrar,id_,clinica)
def estado_cuenta(c):c.saldo_pendiente=max(Decimal("0"),c.monto_total-c.monto_pagado);c.estado="pagada" if c.saldo_pendiente==0 else "parcial" if c.monto_pagado>0 else "vencida" if c.fecha_vencimiento and c.fecha_vencimiento<date.today() else "pendiente"
def estado_cuota(c):c.saldo_pendiente=max(Decimal("0"),c.monto_cuota-c.monto_pagado);c.estado="pagada" if c.saldo_pendiente==0 else "parcial" if c.monto_pagado>0 else "vencida" if c.fecha_vencimiento<date.today() else "pendiente"
def caja_abierta(s,clinica,sede):
 x=s.scalar(select(Caja).where(Caja.clinica_id==clinica,Caja.sede_id==sede,Caja.fecha_operativa==date.today(),Caja.estado=="abierta"))
 if not x:raise HTTPException(409,"Debe existir una caja abierta para la sede y fecha operativa")
 return x

# Sesiones
@router.get("/sesiones-tratamiento/plan/{plan_id}")
def sesiones_plan(plan_id:int,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones")),s:Session=Depends(obtener_sesion)):propio(s,PlanTratamiento,plan_id,u.clinica_id);return [dic(x) for x in s.scalars(select(SesionTratamiento).where(SesionTratamiento.clinica_id==u.clinica_id,SesionTratamiento.plan_tratamiento_id==plan_id).order_by(SesionTratamiento.numero_sesion))]
@router.get("/sesiones-tratamiento/paciente/{paciente_id}")
def sesiones_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [dic(x) for x in s.scalars(select(SesionTratamiento).where(SesionTratamiento.clinica_id==u.clinica_id,SesionTratamiento.paciente_id==paciente_id).order_by(SesionTratamiento.fecha_hora_inicio.desc()))]
@router.get("/sesiones-tratamiento")
def sesiones(u:Usuario=Depends(exigir_permiso("tratamientos_sesiones")),s:Session=Depends(obtener_sesion)):return [dic(x) for x in s.scalars(select(SesionTratamiento).where(SesionTratamiento.clinica_id==u.clinica_id).order_by(SesionTratamiento.fecha_hora_inicio.desc()))]
@router.post("/sesiones-tratamiento",status_code=201)
def crear_sesion(d:SesionCrear,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_crear")),s:Session=Depends(obtener_sesion)):
 p=propio(s,PlanTratamiento,d.plan_tratamiento_id,u.clinica_id)
 if p.estado in ("cancelado","finalizado"):raise HTTPException(409,"No se permiten sesiones para un plan cancelado o finalizado")
 cita=None
 if d.cita_id:
  cita=propio(s,Cita,d.cita_id,u.clinica_id)
  if cita.estado not in ("confirmada","en_atencion"):raise HTTPException(409,"Solo una cita confirmada o en atención puede generar una sesión")
  if cita.plan_tratamiento_id!=p.id or cita.paciente_id!=d.paciente_id:raise HTTPException(422,"La cita, el paciente y el plan no corresponden")
  existente=s.scalar(select(SesionTratamiento.id).where(SesionTratamiento.clinica_id==u.clinica_id,SesionTratamiento.cita_id==cita.id,SesionTratamiento.estado.notin_(("cancelada","anulada"))))
  if existente:raise HTTPException(409,"La cita ya tiene una sesión activa")
 det=s.scalar(select(DetallePlanTratamiento).where(DetallePlanTratamiento.id==d.detalle_plan_tratamiento_id,DetallePlanTratamiento.plan_tratamiento_id==p.id));
 if not det or p.paciente_id!=d.paciente_id:raise HTTPException(400,"Detalle o paciente no corresponde al plan")
 if det.estado not in ("pendiente","en_progreso"):raise HTTPException(409,"Solo se pueden programar procedimientos pendientes o en progreso")
 piezas=list(s.scalars(select(DetallePlanPieza).where(DetallePlanPieza.detalle_plan_tratamiento_id==det.id)))
 numeros={z.numero_pieza for z in piezas}
 if det.tipo_alcance=="pieza":
  pieza=next(iter(numeros),det.pieza_dental)
  if not pieza:raise HTTPException(422,"El procedimiento requiere una pieza vinculada")
 elif det.tipo_alcance=="varias_piezas":
  if not d.pieza_dental or d.pieza_dental not in numeros:raise HTTPException(422,"Seleccione una pieza vinculada al procedimiento")
  pieza=d.pieza_dental
 else:pieza=None
 datos=d.model_dump();datos["procedimiento_realizado"]=det.procedimiento;datos["pieza_dental"]=pieza
 numero=(s.scalar(select(func.max(SesionTratamiento.numero_sesion)).where(SesionTratamiento.plan_tratamiento_id==p.id))or 0)+1;x=SesionTratamiento(clinica_id=u.clinica_id,numero_sesion=numero,**datos);s.add(x);s.flush()
 if cita:cita.estado="en_atencion";auditar(s,u.clinica_id,u.id,"vincular_sesion","agenda_citas","citas",cita.id,nuevos={"sesion_id":x.id})
 auditar(s,u.clinica_id,u.id,"crear","tratamientos_sesiones","sesiones_tratamiento",x.id,nuevos={"cita_id":d.cita_id});s.commit();return dic(x)
@router.get("/citas/{cita_id}/sesion")
def sesion_de_cita(cita_id:int,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones")),s:Session=Depends(obtener_sesion)):
 propio(s,Cita,cita_id,u.clinica_id);x=s.scalar(select(SesionTratamiento).where(SesionTratamiento.clinica_id==u.clinica_id,SesionTratamiento.cita_id==cita_id).order_by(SesionTratamiento.id.desc()));return dic(x) if x else None
@router.post("/citas/{cita_id}/sesion",status_code=201)
def crear_sesion_desde_cita(cita_id:int,d:SesionDesdeCitaCrear,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_crear")),s:Session=Depends(obtener_sesion)):
 cita=propio(s,Cita,cita_id,u.clinica_id)
 if not cita.plan_tratamiento_id:raise HTTPException(409,"La cita debe estar vinculada a un plan")
 det=s.scalar(select(DetallePlanTratamiento).where(DetallePlanTratamiento.id==d.detalle_plan_tratamiento_id,DetallePlanTratamiento.plan_tratamiento_id==cita.plan_tratamiento_id))
 if not det:raise HTTPException(422,"El procedimiento no pertenece al plan de la cita")
 datos=SesionCrear(sede_id=cita.sede_id,plan_tratamiento_id=cita.plan_tratamiento_id,detalle_plan_tratamiento_id=det.id,paciente_id=cita.paciente_id,odontologo_id=cita.odontologo_id,cita_id=cita.id,fecha_hora_inicio=cita.fecha_hora_inicio,fecha_hora_fin=None,procedimiento_realizado=det.procedimiento,pieza_dental=d.pieza_dental,observaciones=d.observaciones,indicaciones=d.indicaciones)
 return crear_sesion(datos,u,s)
@router.get("/sesiones-tratamiento/{id_}")
def sesion(id_:int,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones")),s:Session=Depends(obtener_sesion)):x=propio(s,SesionTratamiento,id_,u.clinica_id);return {**dic(x),"insumos":[dic(i) for i in s.scalars(select(InsumoSesion).where(InsumoSesion.sesion_tratamiento_id==x.id))]}
@router.put("/sesiones-tratamiento/{id_}")
def editar_sesion(id_:int,d:SesionActualizar,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado=="realizada":raise HTTPException(409,"Una sesión realizada no puede editarse")
 for k,v in d.model_dump(exclude_unset=True).items():setattr(x,k,v)
 auditar(s,u.clinica_id,u.id,"editar","tratamientos_sesiones","sesiones_tratamiento",x.id);s.commit();return dic(x)
@router.patch("/sesiones-tratamiento/{id_}/iniciar")
def iniciar_sesion(id_:int,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado not in ("programada","reprogramada"):raise HTTPException(409,"La sesión no puede iniciarse")
 x.estado="en_atencion";s.commit();return dic(x)
@router.patch("/sesiones-tratamiento/{id_}/finalizar")
def finalizar_sesion(id_:int,d:FinalizarSesion,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado=="realizada":raise HTTPException(409,"La sesión ya fue finalizada")
 if x.estado in ("cancelada","suspendida"):raise HTTPException(409,"La sesión no puede finalizarse")
 det=s.get(DetallePlanTratamiento,x.detalle_plan_tratamiento_id);plan=propio(s,PlanTratamiento,x.plan_tratamiento_id,u.clinica_id);x.estado="realizada";x.resultado=d.resultado;x.observaciones=d.observaciones;x.indicaciones=d.indicaciones;x.fecha_hora_fin=d.fecha_hora_fin or datetime.now(timezone.utc);x.proxima_sesion_fecha=d.proxima_sesion_fecha;det.sesiones_completadas=min(det.cantidad_sesiones,det.sesiones_completadas+1);det.estado="completado" if det.sesiones_completadas>=det.cantidad_sesiones else "en_progreso";s.flush();recalcular_plan(s,plan)
 if x.cita_id:
  cita=propio(s,Cita,x.cita_id,u.clinica_id);cita.estado="atendida"
 hist=s.scalar(select(HistoriaClinica).where(HistoriaClinica.clinica_id==u.clinica_id,HistoriaClinica.paciente_id==x.paciente_id))
 if hist:
  consulta=ConsultaClinica(clinica_id=u.clinica_id,historia_clinica_id=hist.id,paciente_id=x.paciente_id,sede_id=x.sede_id,odontologo_id=x.odontologo_id,motivo_consulta=f"Sesión de tratamiento #{x.numero_sesion}",procedimiento_realizado=x.procedimiento_realizado,diagnostico=x.resultado,observaciones=x.observaciones,indicaciones=x.indicaciones,estado="cerrada",fecha_cierre=x.fecha_hora_fin,odontologo_cierre_id=x.odontologo_id);s.add(consulta);s.flush();x.consulta_clinica_id=consulta.id
 auditar(s,u.clinica_id,u.id,"finalizar","tratamientos_sesiones","sesiones_tratamiento",x.id);s.commit();return dic(x)
@router.patch("/sesiones-tratamiento/{id_}/cancelar")
def cancelar_sesion(id_:int,d:MotivoOperacion,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado=="realizada":raise HTTPException(409,"Use anulación para una sesión realizada")
 x.estado="cancelada";x.motivo_cancelacion=d.motivo;x.fecha_cancelacion=datetime.now(timezone.utc);x.usuario_cancelacion_id=u.id;auditar(s,u.clinica_id,u.id,"cancelar","tratamientos_sesiones","sesiones_tratamiento",x.id);s.commit();return dic(x)
@router.patch("/sesiones-tratamiento/{id_}/anular")
def anular_sesion(id_:int,d:MotivoOperacion,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado!="realizada":raise HTTPException(409,"Solo una sesión realizada puede anularse")
 det=s.get(DetallePlanTratamiento,x.detalle_plan_tratamiento_id);plan=propio(s,PlanTratamiento,x.plan_tratamiento_id,u.clinica_id);det.sesiones_completadas=max(0,det.sesiones_completadas-1);det.estado="pendiente" if det.sesiones_completadas==0 else "en_progreso";x.estado="anulada";x.motivo_cancelacion=d.motivo;x.fecha_cancelacion=datetime.now(timezone.utc);x.usuario_cancelacion_id=u.id;s.flush();recalcular_plan(s,plan);auditar(s,u.clinica_id,u.id,"anular","tratamientos_sesiones","sesiones_tratamiento",x.id);s.commit();return dic(x)
@router.patch("/sesiones-tratamiento/{id_}/reprogramar")
def reprogramar_sesion(id_:int,d:ReprogramarSesion,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=propio(s,SesionTratamiento,id_,u.clinica_id)
 if x.estado=="realizada":raise HTTPException(409,"Sesión ya realizada")
 x.fecha_hora_inicio=d.fecha_hora_inicio;x.fecha_hora_fin=d.fecha_hora_fin;x.estado="reprogramada";x.observaciones=d.motivo;auditar(s,u.clinica_id,u.id,"reprogramar","tratamientos_sesiones","sesiones_tratamiento",x.id);s.commit();return dic(x)
@router.post("/sesiones-tratamiento/{id_}/insumos",status_code=201)
def agregar_insumo(id_:int,d:InsumoCrear,u:Usuario=Depends(exigir_permiso("tratamientos_sesiones","puede_editar")),s:Session=Depends(obtener_sesion)):x=propio(s,SesionTratamiento,id_,u.clinica_id);i=InsumoSesion(sesion_tratamiento_id=x.id,**d.model_dump());s.add(i);s.commit();return dic(i)

# Cuentas
@router.get("/cuentas-por-cobrar/paciente/{paciente_id}")
def cuentas_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [dic(x) for x in s.scalars(select(CuentaPorCobrar).where(CuentaPorCobrar.clinica_id==u.clinica_id,CuentaPorCobrar.paciente_id==paciente_id))]
@router.get("/cuentas-por-cobrar")
def cuentas(estado:str|None=None,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):
 q=select(CuentaPorCobrar).where(CuentaPorCobrar.clinica_id==u.clinica_id);q=q.where(CuentaPorCobrar.estado==estado) if estado else q;return [dic(x) for x in s.scalars(q.order_by(CuentaPorCobrar.fecha_creacion.desc()))]
@router.post("/cuentas-por-cobrar",status_code=201)
def crear_cuenta(d:CuentaCrear,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_crear")),s:Session=Depends(obtener_sesion)):
 paciente_propio(s,d.paciente_id,u.clinica_id)
 if d.plan_tratamiento_id:
  p=propio(s,PlanTratamiento,d.plan_tratamiento_id,u.clinica_id)
  if p.estado not in ("aprobado","activo"):raise HTTPException(409,"Solo un plan aprobado o activo puede generar deuda")
  if not s.scalar(select(DetallePlanTratamiento.id).where(DetallePlanTratamiento.plan_tratamiento_id==p.id)):raise HTTPException(422,"El plan debe tener al menos un procedimiento antes de generar deuda")
  if p.costo_total_estimado<=0 or d.monto_total<=0:raise HTTPException(422,"El plan debe tener un total mayor que cero")
  duplicada=s.scalar(select(CuentaPorCobrar.id).where(CuentaPorCobrar.clinica_id==u.clinica_id,CuentaPorCobrar.plan_tratamiento_id==p.id,CuentaPorCobrar.saldo_pendiente>0,CuentaPorCobrar.estado.notin_(("anulada","pagada"))))
  if duplicada and not d.confirmar_duplicado:raise HTTPException(409,f"El plan ya tiene una cuenta activa (#{duplicada}). Confirme expresamente para crear otra.")
 if d.cotizacion_id:
  c=propio(s,Cotizacion,d.cotizacion_id,u.clinica_id)
  if c.estado not in ("aceptada","convertida"):raise HTTPException(409,"La cotización aún no puede generar deuda")
 if d.cuotas and sum((q.monto_cuota for q in d.cuotas),Decimal("0"))!=d.monto_total:raise HTTPException(422,"La suma de cuotas debe coincidir con el total")
 datos=d.model_dump(exclude={"cuotas","confirmar_duplicado"});x=CuentaPorCobrar(clinica_id=u.clinica_id,monto_pagado=0,saldo_pendiente=d.monto_total,**datos);s.add(x);s.flush()
 for q in d.cuotas:s.add(CuotaCuentaPorCobrar(cuenta_por_cobrar_id=x.id,monto_pagado=0,saldo_pendiente=q.monto_cuota,**q.model_dump()))
 auditar(s,u.clinica_id,u.id,"crear","pagos_caja","cuentas_por_cobrar",x.id);s.commit();return dic(x)
@router.post("/cuentas-por-cobrar/desde-plan/{plan_id}",status_code=201)
def cuenta_desde_plan(plan_id:int,sede_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_crear")),s:Session=Depends(obtener_sesion)):
 p=propio(s,PlanTratamiento,plan_id,u.clinica_id)
 return crear_cuenta(CuentaCrear(sede_id=sede_id,paciente_id=p.paciente_id,plan_tratamiento_id=p.id,cotizacion_id=p.cotizacion_id,descripcion=f"Plan {p.numero_plan}",monto_total=p.costo_total_estimado),u,s)
@router.get("/cuentas-por-cobrar/{id_}")
def cuenta(id_:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):x=cuenta_propia(s,id_,u.clinica_id);return {**dic(x),"cuotas":[dic(q) for q in s.scalars(select(CuotaCuentaPorCobrar).where(CuotaCuentaPorCobrar.cuenta_por_cobrar_id==x.id).order_by(CuotaCuentaPorCobrar.numero_cuota))]}
@router.put("/cuentas-por-cobrar/{id_}")
def editar_cuenta(id_:int,d:CuentaActualizar,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_editar")),s:Session=Depends(obtener_sesion)):
 x=cuenta_propia(s,id_,u.clinica_id)
 if x.estado=="pagada":raise HTTPException(409,"Una cuenta pagada no puede modificarse")
 for k,v in d.model_dump(exclude_unset=True).items():setattr(x,k,v)
 s.commit();return dic(x)
@router.post("/cuentas-por-cobrar/{id_}/cuotas",status_code=201)
def agregar_cuota(id_:int,d:CuotaCrear,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_editar")),s:Session=Depends(obtener_sesion)):x=cuenta_propia(s,id_,u.clinica_id);q=CuotaCuentaPorCobrar(cuenta_por_cobrar_id=x.id,monto_pagado=0,saldo_pendiente=d.monto_cuota,**d.model_dump());s.add(q);s.commit();return dic(q)
@router.put("/cuentas-por-cobrar/{id_}/cuotas/{cuota_id}")
def editar_cuota(id_:int,cuota_id:int,d:CuotaCrear,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_editar")),s:Session=Depends(obtener_sesion)):
 cuenta_propia(s,id_,u.clinica_id);q=s.scalar(select(CuotaCuentaPorCobrar).where(CuotaCuentaPorCobrar.id==cuota_id,CuotaCuentaPorCobrar.cuenta_por_cobrar_id==id_))
 if not q:raise HTTPException(404,"Cuota no encontrada")
 if q.estado=="pagada":raise HTTPException(409,"Una cuota pagada no puede modificarse")
 for k,v in d.model_dump().items():setattr(q,k,v)
 estado_cuota(q);s.commit();return dic(q)
@router.get("/cuentas-por-cobrar/{id_}/estado-cuenta")
def obtener_estado_cuenta(id_:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):x=cuenta_propia(s,id_,u.clinica_id);return {"estado":x.estado,"monto_total":x.monto_total,"monto_pagado":x.monto_pagado,"saldo_pendiente":x.saldo_pendiente}

# Caja
@router.post("/cajas/abrir",status_code=201)
def abrir_caja(d:AbrirCaja,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_crear")),s:Session=Depends(obtener_sesion)):
 if s.scalar(select(Caja.id).where(Caja.clinica_id==u.clinica_id,Caja.sede_id==d.sede_id,Caja.fecha_operativa==date.today(),Caja.estado=="abierta")):raise HTTPException(409,"Ya existe una caja abierta para esta sede y fecha")
 x=Caja(clinica_id=u.clinica_id,usuario_apertura_id=u.id,fecha_operativa=date.today(),**d.model_dump());s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"abrir","pagos_caja","cajas",x.id);s.commit();return dic(x)
@router.get("/cajas/actual")
def caja_actual(sede_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):return dic(caja_abierta(s,u.clinica_id,sede_id))
@router.get("/cajas")
def cajas(u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):return [dic(x) for x in s.scalars(select(Caja).where(Caja.clinica_id==u.clinica_id).order_by(Caja.fecha_apertura.desc()))]
@router.get("/cajas/resumen-diario")
def resumen_diario(sede_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):
 c=caja_abierta(s,u.clinica_id,sede_id);filas=s.execute(select(MovimientoCaja.metodo_pago,func.sum(MovimientoCaja.monto)).where(MovimientoCaja.caja_id==c.id,MovimientoCaja.tipo_movimiento=="ingreso").group_by(MovimientoCaja.metodo_pago));return {"caja":dic(c),"por_metodo":{m:v for m,v in filas}}
@router.get("/cajas/{id_}")
def caja(id_:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):return dic(propio(s,Caja,id_,u.clinica_id))
@router.get("/cajas/{id_}/movimientos")
def movimientos_caja(id_:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):propio(s,Caja,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(MovimientoCaja).where(MovimientoCaja.caja_id==id_).order_by(MovimientoCaja.fecha_movimiento.desc()))]
@router.post("/cajas/{id_}/movimientos-egreso",status_code=201)
def egreso_caja(id_:int,d:MovimientoManual,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_crear")),s:Session=Depends(obtener_sesion)):c=propio(s,Caja,id_,u.clinica_id);x=MovimientoCaja(clinica_id=u.clinica_id,sede_id=c.sede_id,caja_id=c.id,tipo_movimiento="egreso",usuario_id=u.id,**d.model_dump());s.add(x);auditar(s,u.clinica_id,u.id,"egreso","pagos_caja","movimientos_caja",c.id);s.commit();return dic(x)
@router.post("/cajas/{id_}/ajustes",status_code=201)
def ajuste_caja(id_:int,d:MovimientoManual,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_editar")),s:Session=Depends(obtener_sesion)):c=propio(s,Caja,id_,u.clinica_id);x=MovimientoCaja(clinica_id=u.clinica_id,sede_id=c.sede_id,caja_id=c.id,tipo_movimiento="ajuste",usuario_id=u.id,**d.model_dump());s.add(x);auditar(s,u.clinica_id,u.id,"ajuste","pagos_caja","movimientos_caja",c.id);s.commit();return dic(x)
@router.post("/cajas/{id_}/cerrar")
def cerrar_caja(id_:int,d:CerrarCaja,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_editar")),s:Session=Depends(obtener_sesion)):
 c=propio(s,Caja,id_,u.clinica_id)
 if c.estado!="abierta":raise HTTPException(409,"La caja ya está cerrada")
 ingresos=s.scalar(select(func.coalesce(func.sum(MovimientoCaja.monto),0)).where(MovimientoCaja.caja_id==c.id,MovimientoCaja.metodo_pago=="efectivo",MovimientoCaja.tipo_movimiento=="ingreso"));egresos=s.scalar(select(func.coalesce(func.sum(MovimientoCaja.monto),0)).where(MovimientoCaja.caja_id==c.id,MovimientoCaja.metodo_pago=="efectivo",MovimientoCaja.tipo_movimiento=="egreso"));ajustes=s.scalar(select(func.coalesce(func.sum(MovimientoCaja.monto),0)).where(MovimientoCaja.caja_id==c.id,MovimientoCaja.metodo_pago=="efectivo",MovimientoCaja.tipo_movimiento=="ajuste"));calculado=c.monto_inicial+ingresos-egresos+ajustes;diferencia=d.monto_final_declarado-calculado
 if diferencia!=0 and not d.observaciones_cierre:raise HTTPException(422,"Debe indicar una observación cuando existe diferencia")
 c.monto_final_calculado=calculado;c.monto_final_declarado=d.monto_final_declarado;c.diferencia=diferencia;c.observaciones_cierre=d.observaciones_cierre;c.usuario_cierre_id=u.id;c.fecha_cierre=datetime.now(timezone.utc);c.estado="cerrada";auditar(s,u.clinica_id,u.id,"cerrar","pagos_caja","cajas",c.id);s.commit();return dic(c)

# Pagos
@router.get("/pagos/paciente/{paciente_id}")
def pagos_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [dic(x) for x in s.scalars(select(Pago).where(Pago.clinica_id==u.clinica_id,Pago.paciente_id==paciente_id))]
@router.get("/pagos/cuenta/{cuenta_id}")
def pagos_cuenta(cuenta_id:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):cuenta_propia(s,cuenta_id,u.clinica_id);ids=select(AplicacionPago.pago_id).where(AplicacionPago.cuenta_por_cobrar_id==cuenta_id);return [dic(x) for x in s.scalars(select(Pago).where(Pago.id.in_(ids)))]
@router.get("/pagos")
def pagos(u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):return [dic(x) for x in s.scalars(select(Pago).where(Pago.clinica_id==u.clinica_id).order_by(Pago.fecha_hora_pago.desc()))]
@router.post("/pagos",status_code=201)
def registrar_pago(d:PagoCrear,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_crear")),s:Session=Depends(obtener_sesion)):
 existente=s.scalar(select(Pago).where(Pago.clinica_id==u.clinica_id,Pago.codigo_idempotencia==d.codigo_idempotencia))
 if existente:return dic(existente)
 paciente_propio(s,d.paciente_id,u.clinica_id);caja=caja_abierta(s,u.clinica_id,d.sede_id);efectivo=sum((x.monto for x in d.detalles if x.metodo_pago=="efectivo"),Decimal("0"))
 if d.vuelto>efectivo:raise HTTPException(422,"El vuelto no puede superar el efectivo recibido")
 monto_aplicado=sum((x.monto_aplicado for x in d.aplicaciones),Decimal("0"));cuentas={}
 for a in d.aplicaciones:
  c=s.scalar(select(CuentaPorCobrar).where(CuentaPorCobrar.id==a.cuenta_por_cobrar_id,CuentaPorCobrar.clinica_id==u.clinica_id,CuentaPorCobrar.paciente_id==d.paciente_id).with_for_update())
  if not c or c.estado in ("anulada","pagada"):raise HTTPException(409,"Cuenta inválida o sin saldo")
  q=None
  if a.cuota_cuenta_por_cobrar_id:
   q=s.scalar(select(CuotaCuentaPorCobrar).where(CuotaCuentaPorCobrar.id==a.cuota_cuenta_por_cobrar_id,CuotaCuentaPorCobrar.cuenta_por_cobrar_id==c.id).with_for_update())
   if not q or q.estado=="pagada" or a.monto_aplicado>q.saldo_pendiente:raise HTTPException(409,"Cuota inválida o aplicación superior al saldo")
  if a.monto_aplicado>c.saldo_pendiente:raise HTTPException(409,"La aplicación supera el saldo de la cuenta")
  cuentas[c.id]=(c,q)
 codigo=f"PAG-{datetime.now().year}-{(s.scalar(select(func.count(Pago.id)).where(Pago.clinica_id==u.clinica_id))or 0)+1:08d}";primera=d.aplicaciones[0];p=Pago(clinica_id=u.clinica_id,sede_id=d.sede_id,paciente_id=d.paciente_id,cuenta_por_cobrar_id=primera.cuenta_por_cobrar_id,cuota_cuenta_por_cobrar_id=primera.cuota_cuenta_por_cobrar_id,caja_id=caja.id,usuario_registro_id=u.id,codigo_idempotencia=d.codigo_idempotencia,codigo_interno=codigo,monto_total=d.monto_total,monto_aplicado=monto_aplicado,vuelto=d.vuelto,observaciones=d.observaciones);s.add(p);s.flush()
 for x in d.detalles:s.add(DetallePago(pago_id=p.id,**x.model_dump()))
 for a in d.aplicaciones:
  c,q=cuentas[a.cuenta_por_cobrar_id];s.add(AplicacionPago(pago_id=p.id,**a.model_dump()));c.monto_pagado+=a.monto_aplicado;estado_cuenta(c)
  if q:q.monto_pagado+=a.monto_aplicado;estado_cuota(q)
 vuelto=d.vuelto
 for x in d.detalles:
  monto=x.monto
  if x.metodo_pago=="efectivo" and vuelto:monto-=vuelto;vuelto=Decimal("0")
  if monto>0:s.add(MovimientoCaja(clinica_id=u.clinica_id,sede_id=d.sede_id,caja_id=caja.id,pago_id=p.id,tipo_movimiento="ingreso",metodo_pago=x.metodo_pago,monto=monto,descripcion=f"Pago {codigo}",usuario_id=u.id))
 auditar(s,u.clinica_id,u.id,"crear","pagos_caja","pagos",p.id,nuevos={"codigo":codigo,"monto_aplicado":str(monto_aplicado)});s.commit();return dic(p)
@router.get("/pagos/{id_}")
def pago(id_:int,u:Usuario=Depends(exigir_permiso("pagos_caja")),s:Session=Depends(obtener_sesion)):
 p=propio(s,Pago,id_,u.clinica_id);return {**dic(p),"detalles":[dic(x) for x in s.scalars(select(DetallePago).where(DetallePago.pago_id==p.id))],"aplicaciones":[dic(x) for x in s.scalars(select(AplicacionPago).where(AplicacionPago.pago_id==p.id))]}
@router.patch("/pagos/{id_}/anular")
def anular_pago(id_:int,d:MotivoOperacion,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_eliminar")),s:Session=Depends(obtener_sesion)):
 p=propio(s,Pago,id_,u.clinica_id)
 if p.estado!="registrado":raise HTTPException(409,"El pago no puede anularse")
 for a in s.scalars(select(AplicacionPago).where(AplicacionPago.pago_id==p.id)):
  neto=a.monto_aplicado-a.monto_devuelto;c=cuenta_propia(s,a.cuenta_por_cobrar_id,u.clinica_id);c.monto_pagado-=neto;estado_cuenta(c)
  if a.cuota_cuenta_por_cobrar_id:q=s.get(CuotaCuentaPorCobrar,a.cuota_cuenta_por_cobrar_id);q.monto_pagado-=neto;estado_cuota(q)
 for m in s.scalars(select(MovimientoCaja).where(MovimientoCaja.pago_id==p.id,MovimientoCaja.tipo_movimiento=="ingreso")):s.add(MovimientoCaja(clinica_id=u.clinica_id,sede_id=m.sede_id,caja_id=m.caja_id,pago_id=p.id,tipo_movimiento="egreso",metodo_pago=m.metodo_pago,monto=m.monto,descripcion=f"Anulación {p.codigo_interno}",usuario_id=u.id))
 p.estado="anulado";p.motivo_anulacion=d.motivo;p.fecha_anulacion=datetime.now(timezone.utc);p.usuario_anulacion_id=u.id;auditar(s,u.clinica_id,u.id,"anular","pagos_caja","pagos",p.id);s.commit();return dic(p)
@router.post("/pagos/{id_}/devolucion",status_code=201)
def devolver_pago(id_:int,d:DevolucionCrear,u:Usuario=Depends(exigir_permiso("pagos_caja","puede_eliminar")),s:Session=Depends(obtener_sesion)):
 p=propio(s,Pago,id_,u.clinica_id);disponible=p.monto_aplicado-p.monto_devuelto
 if p.estado=="anulado" or d.monto>disponible:raise HTTPException(409,"Monto de devolución inválido")
 restante=d.monto
 for a in s.scalars(select(AplicacionPago).where(AplicacionPago.pago_id==p.id).order_by(AplicacionPago.id.desc())):
  monto=min(restante,a.monto_aplicado-a.monto_devuelto)
  if monto<=0:continue
  a.monto_devuelto+=monto;c=cuenta_propia(s,a.cuenta_por_cobrar_id,u.clinica_id);c.monto_pagado-=monto;estado_cuenta(c)
  if a.cuota_cuenta_por_cobrar_id:q=s.get(CuotaCuentaPorCobrar,a.cuota_cuenta_por_cobrar_id);q.monto_pagado-=monto;estado_cuota(q)
  restante-=monto
  if restante==0:break
 dev=DevolucionPago(pago_id=p.id,monto=d.monto,motivo=d.motivo,usuario_responsable_id=u.id);s.add(dev);p.monto_devuelto+=d.monto;p.estado="devuelto" if p.monto_devuelto==p.monto_aplicado else "devuelto_parcial";auditar(s,u.clinica_id,u.id,"devolver","pagos_caja","pagos",p.id,nuevos={"monto":str(d.monto)});s.commit();return dic(dev)

# Comprobantes
@router.post("/comprobantes-internos",status_code=201)
def emitir_comprobante(d:ComprobanteCrear,u:Usuario=Depends(exigir_permiso("comprobantes_facturacion","puede_crear")),s:Session=Depends(obtener_sesion)):
 p=propio(s,Pago,d.pago_id,u.clinica_id)
 if p.estado=="anulado":raise HTTPException(409,"No se emite comprobante de un pago anulado")
 existente=s.scalar(select(ComprobanteInterno).where(ComprobanteInterno.pago_id==p.id))
 if existente:return dic(existente)
 clinica=s.get(Clinica,u.clinica_id);pac=s.get(Paciente,p.paciente_id);det=[jsonable_encoder(dic(x)) for x in s.scalars(select(DetallePago).where(DetallePago.pago_id==p.id))];aps=[jsonable_encoder(dic(x)) for x in s.scalars(select(AplicacionPago).where(AplicacionPago.pago_id==p.id))];numero=f"REC-{datetime.now().year}-{(s.scalar(select(func.count(ComprobanteInterno.id)).where(ComprobanteInterno.clinica_id==u.clinica_id))or 0)+1:08d}";x=ComprobanteInterno(clinica_id=u.clinica_id,sede_id=p.sede_id,pago_id=p.id,paciente_id=p.paciente_id,numero_comprobante=numero,concepto=d.concepto,monto=p.monto_aplicado,observaciones=d.observaciones,fotografia_clinica=jsonable_encoder(dic(clinica)),fotografia_paciente=jsonable_encoder(dic(pac)),fotografia_metodos_pago=det,fotografia_aplicaciones=aps,fotografia_pago=jsonable_encoder(dic(p)),fotografia_usuario=jsonable_encoder(dic(u,("contrasena_hash",))));s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"emitir","comprobantes_facturacion","comprobantes_internos",x.id);s.commit();return dic(x)
@router.get("/comprobantes-internos")
def comprobantes(u:Usuario=Depends(exigir_permiso("comprobantes_facturacion")),s:Session=Depends(obtener_sesion)):return [dic(x) for x in s.scalars(select(ComprobanteInterno).where(ComprobanteInterno.clinica_id==u.clinica_id).order_by(ComprobanteInterno.fecha_emision.desc()))]
@router.get("/comprobantes-internos/{id_}")
def comprobante(id_:int,u:Usuario=Depends(exigir_permiso("comprobantes_facturacion")),s:Session=Depends(obtener_sesion)):return dic(propio(s,ComprobanteInterno,id_,u.clinica_id))
@router.post("/comprobantes-internos/{id_}/generar-pdf")
def pdf_comprobante(id_:int,u:Usuario=Depends(exigir_permiso("comprobantes_facturacion")),s:Session=Depends(obtener_sesion)):x=propio(s,ComprobanteInterno,id_,u.clinica_id);return Response(pdf_basico(f"Recibo interno {x.numero_comprobante}",["NO VALIDO COMO COMPROBANTE SUNAT",f"Total aplicado: S/ {x.monto}"]),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{x.numero_comprobante}.pdf"'})
@router.patch("/comprobantes-internos/{id_}/anular")
def anular_comprobante(id_:int,d:MotivoOperacion,u:Usuario=Depends(exigir_permiso("comprobantes_facturacion","puede_eliminar")),s:Session=Depends(obtener_sesion)):x=propio(s,ComprobanteInterno,id_,u.clinica_id);x.estado="anulado";x.motivo_anulacion=d.motivo;auditar(s,u.clinica_id,u.id,"anular","comprobantes_facturacion","comprobantes_internos",x.id);s.commit();return dic(x)
