from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from app.db.sesion import obtener_sesion
from app.dependencias.seguridad import exigir_permiso
from app.esquemas.fase1 import *
from app.modelos import *
from app.servicios.auditoria import auditar

router=APIRouter(prefix="/api")
FDI={*range(11,19),*range(21,29),*range(31,39),*range(41,49)}
FDI_TEMPORAL={*range(51,56),*range(61,66),*range(71,76),*range(81,86)}
SUCESORES={**{50+i:10+i for i in range(1,6)},**{60+i:20+i for i in range(1,6)},**{70+i:30+i for i in range(1,6)},**{80+i:40+i for i in range(1,6)}}
def dic(x,excluir=()):return {c.name:getattr(x,c.name) for c in x.__table__.columns if c.name not in excluir}
def asignar(x,d):
    for k,v in d.items():
        if v is not None and hasattr(x,k):setattr(x,k,v)
def propio(s,modelo,id_,clinica_id):
    x=s.scalar(select(modelo).where(modelo.id==id_,modelo.clinica_id==clinica_id))
    if not x:raise HTTPException(404,"Registro no encontrado")
    return x
def paciente_propio(s,id_,clinica_id):return propio(s,Paciente,id_,clinica_id)
def validar_relaciones(s,u,paciente_id,sede_id=None,odontologo_id=None):
    paciente_propio(s,paciente_id,u.clinica_id)
    if sede_id and not s.scalar(select(Sede.id).where(Sede.id==sede_id,Sede.clinica_id==u.clinica_id)):raise HTTPException(400,"La sede no pertenece a la clínica")
    if odontologo_id and not s.scalar(select(Usuario.id).where(Usuario.id==odontologo_id,Usuario.clinica_id==u.clinica_id,Usuario.estado.is_(True))):raise HTTPException(400,"El odontólogo no pertenece a la clínica")
def correlativo(s,modelo,clinica_id,prefijo):return f"{prefijo}-{datetime.now().year}-{(s.scalar(select(func.count(modelo.id)).where(modelo.clinica_id==clinica_id)) or 0)+1:06d}"

# Pacientes
@router.get("/pacientes/buscar")
def buscar_pacientes(q:str=Query(min_length=1),u:Usuario=Depends(exigir_permiso("pacientes")),s:Session=Depends(obtener_sesion)):
    p=f"%{q}%";xs=s.scalars(select(Paciente).where(Paciente.clinica_id==u.clinica_id,or_(Paciente.numero_documento.ilike(p),Paciente.nombres.ilike(p),Paciente.apellidos.ilike(p),Paciente.telefono.ilike(p),Paciente.correo.ilike(p))).limit(20));return [dic(x) for x in xs]
@router.get("/pacientes")
def listar_pacientes(q:str|None=None,estado:bool|None=None,sexo:str|None=None,edad_minima:int|None=None,edad_maxima:int|None=None,pagina:int=1,limite:int=Query(20,le=100),u:Usuario=Depends(exigir_permiso("pacientes")),s:Session=Depends(obtener_sesion)):
    filtros=[Paciente.clinica_id==u.clinica_id]
    if q:
        p=f"%{q}%";filtros.append(or_(Paciente.numero_documento.ilike(p),Paciente.nombres.ilike(p),Paciente.apellidos.ilike(p),Paciente.telefono.ilike(p),Paciente.correo.ilike(p)))
    if estado is not None:filtros.append(Paciente.estado==estado)
    if sexo:filtros.append(Paciente.sexo==sexo)
    hoy=date.today()
    if edad_minima is not None:filtros.append(Paciente.fecha_nacimiento<=date(hoy.year-edad_minima,hoy.month,hoy.day))
    if edad_maxima is not None:filtros.append(Paciente.fecha_nacimiento>=date(hoy.year-edad_maxima-1,hoy.month,hoy.day))
    total=s.scalar(select(func.count(Paciente.id)).where(*filtros));xs=s.scalars(select(Paciente).where(*filtros).order_by(Paciente.apellidos).offset((pagina-1)*limite).limit(limite));return {"datos":[dic(x) for x in xs],"total":total,"pagina":pagina,"limite":limite}
@router.post("/pacientes",status_code=201)
def crear_paciente(d:PacienteCrear,u:Usuario=Depends(exigir_permiso("pacientes","puede_crear")),s:Session=Depends(obtener_sesion)):
    if d.sede_id and not s.scalar(select(Sede.id).where(Sede.id==d.sede_id,Sede.clinica_id==u.clinica_id)):raise HTTPException(400,"La sede no pertenece a la clínica")
    if d.numero_documento and s.scalar(select(Paciente.id).where(Paciente.clinica_id==u.clinica_id,Paciente.numero_documento==d.numero_documento)):raise HTTPException(409,"El documento ya está registrado")
    x=Paciente(clinica_id=u.clinica_id,**d.model_dump(mode="python"));s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"crear","pacientes","pacientes",x.id,nuevos=d.model_dump(mode="json"));s.commit();return dic(x)
@router.get("/pacientes/{id_}/resumen")
def resumen_paciente(id_:int,u:Usuario=Depends(exigir_permiso("pacientes")),s:Session=Depends(obtener_sesion)):
    p=paciente_propio(s,id_,u.clinica_id);alergias=[dic(x) for x in s.scalars(select(AlergiaPaciente).where(AlergiaPaciente.paciente_id==id_,AlergiaPaciente.activo.is_(True)))];ant=[dic(x) for x in s.scalars(select(AntecedenteMedico).where(AntecedenteMedico.paciente_id==id_,AntecedenteMedico.activo.is_(True)))];citas=[dic(x) for x in s.scalars(select(Cita).where(Cita.paciente_id==id_,Cita.clinica_id==u.clinica_id).order_by(Cita.fecha_hora_inicio.desc()).limit(5))];return {"paciente":dic(p),"alergias":alergias,"antecedentes":ant,"ultimas_citas":citas,"cotizaciones":s.scalar(select(func.count(Cotizacion.id)).where(Cotizacion.paciente_id==id_)),"planes":s.scalar(select(func.count(PlanTratamiento.id)).where(PlanTratamiento.paciente_id==id_))}
@router.get("/pacientes/{id_}")
def obtener_paciente(id_:int,u:Usuario=Depends(exigir_permiso("pacientes")),s:Session=Depends(obtener_sesion)):return dic(paciente_propio(s,id_,u.clinica_id))
@router.put("/pacientes/{id_}")
def editar_paciente(id_:int,d:PacienteActualizar,u:Usuario=Depends(exigir_permiso("pacientes","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=paciente_propio(s,id_,u.clinica_id);antes=dic(x);asignar(x,d.model_dump(exclude_unset=True));auditar(s,u.clinica_id,u.id,"editar","pacientes","pacientes",x.id,antes,d.model_dump(mode="json"));s.commit();return dic(x)
@router.patch("/pacientes/{id_}/estado")
def estado_paciente(id_:int,d:EstadoPaciente,u:Usuario=Depends(exigir_permiso("pacientes","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=paciente_propio(s,id_,u.clinica_id);x.estado=d.estado;auditar(s,u.clinica_id,u.id,"cambiar_estado","pacientes","pacientes",x.id,nuevos={"estado":d.estado});s.commit();return dic(x)
@router.post("/pacientes/{id_}/antecedentes",status_code=201)
def crear_antecedente(id_:int,d:AntecedenteCrear,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_crear")),s:Session=Depends(obtener_sesion)):
    paciente_propio(s,id_,u.clinica_id);x=AntecedenteMedico(paciente_id=id_,**d.model_dump());s.add(x);s.commit();return dic(x)
@router.get("/pacientes/{id_}/antecedentes")
def antecedentes(id_:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):paciente_propio(s,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(AntecedenteMedico).where(AntecedenteMedico.paciente_id==id_))]
@router.post("/pacientes/{id_}/alergias",status_code=201)
def crear_alergia(id_:int,d:AlergiaCrear,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_crear")),s:Session=Depends(obtener_sesion)):
    paciente_propio(s,id_,u.clinica_id);x=AlergiaPaciente(paciente_id=id_,**d.model_dump());s.add(x);s.commit();return dic(x)
@router.get("/pacientes/{id_}/alergias")
def alergias(id_:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):paciente_propio(s,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(AlergiaPaciente).where(AlergiaPaciente.paciente_id==id_))]

# Historia clínica
@router.get("/historias-clinicas/paciente/{paciente_id}")
def historia(paciente_id:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):
    paciente_propio(s,paciente_id,u.clinica_id);x=s.scalar(select(HistoriaClinica).where(HistoriaClinica.clinica_id==u.clinica_id,HistoriaClinica.paciente_id==paciente_id));
    if not x:raise HTTPException(404,"Historia clínica no encontrada")
    return dic(x)
@router.post("/historias-clinicas/paciente/{paciente_id}",status_code=201)
def crear_historia(paciente_id:int,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_crear")),s:Session=Depends(obtener_sesion)):
    paciente_propio(s,paciente_id,u.clinica_id)
    if s.scalar(select(HistoriaClinica.id).where(HistoriaClinica.clinica_id==u.clinica_id,HistoriaClinica.paciente_id==paciente_id)):raise HTTPException(409,"El paciente ya tiene historia clínica")
    x=HistoriaClinica(clinica_id=u.clinica_id,paciente_id=paciente_id,numero_historia=correlativo(s,HistoriaClinica,u.clinica_id,"HC"));s.add(x);s.commit();return dic(x)
@router.get("/consultas-clinicas")
def consultas(paciente_id:int|None=None,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):
    q=select(ConsultaClinica).where(ConsultaClinica.clinica_id==u.clinica_id);q=q.where(ConsultaClinica.paciente_id==paciente_id) if paciente_id else q;return [dic(x) for x in s.scalars(q.order_by(ConsultaClinica.fecha_consulta.desc()))]
@router.post("/consultas-clinicas",status_code=201)
def crear_consulta(d:ConsultaCrear,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_crear")),s:Session=Depends(obtener_sesion)):
    validar_relaciones(s,u,d.paciente_id,d.sede_id,d.odontologo_id);h=s.scalar(select(HistoriaClinica).where(HistoriaClinica.clinica_id==u.clinica_id,HistoriaClinica.paciente_id==d.paciente_id))
    if not h:raise HTTPException(400,"Debe crear primero la historia clínica")
    x=ConsultaClinica(clinica_id=u.clinica_id,historia_clinica_id=h.id,**d.model_dump(exclude_none=True));s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"crear","historia_clinica","consultas_clinicas",x.id,nuevos=d.model_dump(mode="json"));s.commit();return dic(x)
@router.get("/consultas-clinicas/{id_}")
def consulta(id_:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):return dic(propio(s,ConsultaClinica,id_,u.clinica_id))
@router.put("/consultas-clinicas/{id_}")
def editar_consulta(id_:int,d:ConsultaActualizar,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,ConsultaClinica,id_,u.clinica_id)
    if x.estado!="abierta":raise HTTPException(409,"Solo se puede editar una consulta abierta")
    asignar(x,d.model_dump(exclude_unset=True));s.commit();return dic(x)
@router.post("/consultas-clinicas/{id_}/evoluciones",status_code=201)
def crear_evolucion(id_:int,d:EvolucionCrear,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_editar")),s:Session=Depends(obtener_sesion)):
    propio(s,ConsultaClinica,id_,u.clinica_id);x=EvolucionClinica(clinica_id=u.clinica_id,consulta_clinica_id=id_,odontologo_id=u.id,descripcion=d.descripcion);s.add(x);s.commit();return dic(x)
@router.get("/consultas-clinicas/{id_}/evoluciones")
def evoluciones(id_:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):propio(s,ConsultaClinica,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(EvolucionClinica).where(EvolucionClinica.consulta_clinica_id==id_))]
@router.patch("/consultas-clinicas/{id_}/anular")
def anular_consulta(id_:int,d:AnularConsulta,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,ConsultaClinica,id_,u.clinica_id);x.estado="anulada";x.motivo_anulacion=d.motivo;x.fecha_anulacion=datetime.now(timezone.utc);auditar(s,u.clinica_id,u.id,"anular","historia_clinica","consultas_clinicas",x.id,nuevos={"motivo":d.motivo});s.commit();return dic(x)
@router.post("/consultas-clinicas/{id_}/cerrar")
def cerrar_consulta(id_:int,u:Usuario=Depends(exigir_permiso("historia_clinica","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,ConsultaClinica,id_,u.clinica_id)
    if x.odontologo_id!=u.id:raise HTTPException(403,"Solo el odontólogo responsable puede cerrar la consulta")
    x.estado="cerrada";x.fecha_cierre=datetime.now(timezone.utc);x.odontologo_cierre_id=u.id;s.commit();return dic(x)

@router.get("/historias-clinicas/paciente/{paciente_id}/pdf")
def pdf_historia(paciente_id:int,u:Usuario=Depends(exigir_permiso("historia_clinica")),s:Session=Depends(obtener_sesion)):
    p=paciente_propio(s,paciente_id,u.clinica_id);h=s.scalar(select(HistoriaClinica).where(HistoriaClinica.clinica_id==u.clinica_id,HistoriaClinica.paciente_id==paciente_id))
    if not h:raise HTTPException(404,"Historia clínica no encontrada")
    return Response(pdf_basico(f"Historia clinica {h.numero_historia}",[f"Paciente: {p.nombres} {p.apellidos}"]),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{h.numero_historia}.pdf"'})

# Odontograma
@router.get("/odontogramas/paciente/{paciente_id}")
def odontogramas_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("odontograma")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [dic(x) for x in s.scalars(select(Odontograma).where(Odontograma.clinica_id==u.clinica_id,Odontograma.paciente_id==paciente_id).order_by(Odontograma.fecha_registro.desc()))]
@router.post("/odontogramas/paciente/{paciente_id}",status_code=201)
def crear_odontograma(paciente_id:int,d:OdontogramaCrear,u:Usuario=Depends(exigir_permiso("odontograma","puede_crear")),s:Session=Depends(obtener_sesion)):
    validar_relaciones(s,u,paciente_id,odontologo_id=d.odontologo_id);x=Odontograma(clinica_id=u.clinica_id,paciente_id=paciente_id,**d.model_dump());s.add(x);s.flush()
    numeros=FDI if d.tipo_denticion=="permanente" else FDI_TEMPORAL if d.tipo_denticion=="temporal" else FDI|FDI_TEMPORAL
    for n in sorted(numeros):
        temporal=n in FDI_TEMPORAL;s.add(PiezaOdontograma(odontograma_id=x.id,numero_pieza=n,tipo_pieza="temporal" if temporal else "permanente",estado_erupcion="erupcionado" if temporal or d.tipo_denticion=="permanente" else "no_erupcionado",numero_pieza_sucesora=SUCESORES.get(n)))
    auditar(s,u.clinica_id,u.id,"crear","odontograma","odontogramas",x.id,nuevos={"tipo_denticion":d.tipo_denticion});s.commit();return dic(x)
@router.get("/odontogramas/{id_}")
def odontograma(id_:int,u:Usuario=Depends(exigir_permiso("odontograma")),s:Session=Depends(obtener_sesion)):return dic(propio(s,Odontograma,id_,u.clinica_id))
@router.put("/odontogramas/{id_}")
def editar_odontograma(id_:int,d:OdontogramaActualizar,u:Usuario=Depends(exigir_permiso("odontograma","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Odontograma,id_,u.clinica_id);asignar(x,d.model_dump(exclude_unset=True));auditar(s,u.clinica_id,u.id,"editar","odontograma","odontogramas",x.id);s.commit();return dic(x)
@router.get("/odontogramas/{id_}/piezas")
def piezas(id_:int,u:Usuario=Depends(exigir_permiso("odontograma")),s:Session=Depends(obtener_sesion)):propio(s,Odontograma,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(PiezaOdontograma).where(PiezaOdontograma.odontograma_id==id_).order_by(PiezaOdontograma.numero_pieza))]
def validar_estado_pediatrico(numero:int,tipo:str|None,estado_pieza:str|None,perdida:bool|None,sucesora:int|None):
    esperado="temporal" if numero in FDI_TEMPORAL else "permanente" if numero in FDI else None
    if not esperado:raise HTTPException(422,"Número de pieza FDI inválido")
    if tipo and tipo!=esperado:raise HTTPException(422,"El tipo de pieza no corresponde a su numeración FDI")
    if (perdida or estado_pieza in ("exfoliacion_fisiologica","perdida_prematura")) and esperado!="temporal":raise HTTPException(422,"La exfoliación o pérdida prematura solo aplica a piezas temporales")
    if sucesora is not None and SUCESORES.get(numero)!=sucesora:raise HTTPException(422,"La pieza sucesora no corresponde al mapa FDI temporal-permanente")
@router.patch("/odontogramas/{id_}/piezas/{numero}/estado-general")
def actualizar_estado_pieza(id_:int,numero:int,d:PiezaEstadoActualizar,u:Usuario=Depends(exigir_permiso("odontograma","puede_editar")),s:Session=Depends(obtener_sesion)):
    propio(s,Odontograma,id_,u.clinica_id);pieza=s.scalar(select(PiezaOdontograma).where(PiezaOdontograma.odontograma_id==id_,PiezaOdontograma.numero_pieza==numero))
    if not pieza:raise HTTPException(404,"Pieza FDI no encontrada")
    validar_estado_pediatrico(numero,d.tipo_pieza,d.estado_pieza,d.perdida_prematura,d.numero_pieza_sucesora);antes=jsonable_encoder(dic(pieza));asignar(pieza,d.model_dump(exclude_unset=True));auditar(s,u.clinica_id,u.id,"actualizar_estado_pieza","odontograma","piezas_odontograma",pieza.id,antes,d.model_dump(mode="json",exclude_unset=True));s.commit();return dic(pieza)
@router.post("/odontogramas/{id_}/piezas/{numero}/hallazgos",status_code=201)
def crear_hallazgo(id_:int,numero:int,d:HallazgoCrear,u:Usuario=Depends(exigir_permiso("odontograma","puede_editar")),s:Session=Depends(obtener_sesion)):
    propio(s,Odontograma,id_,u.clinica_id);pieza=s.scalar(select(PiezaOdontograma).where(PiezaOdontograma.odontograma_id==id_,PiezaOdontograma.numero_pieza==numero))
    if not pieza:raise HTTPException(404,"Pieza FDI no encontrada")
    validar_estado_pediatrico(numero,d.tipo_pieza,d.estado_pieza,d.perdida_prematura,d.numero_pieza_sucesora);datos=d.model_dump(exclude={"estado_tratamiento"});datos.update(condicion=d.condicion or pieza.condicion,tipo_pieza=d.tipo_pieza or pieza.tipo_pieza,estado_erupcion=d.estado_erupcion or pieza.estado_erupcion,estado_pieza=d.estado_pieza or pieza.estado_pieza,perdida_prematura=d.perdida_prematura if d.perdida_prematura is not None else pieza.perdida_prematura,numero_pieza_sucesora=d.numero_pieza_sucesora if d.numero_pieza_sucesora is not None else pieza.numero_pieza_sucesora);x=HallazgoDental(pieza_odontograma_id=pieza.id,odontologo_id=u.id,**datos);s.add(x)
    if d.condicion:pieza.condicion=d.condicion
    if d.estado_tratamiento:pieza.estado_tratamiento=d.estado_tratamiento
    if d.tipo_pieza:pieza.tipo_pieza=d.tipo_pieza
    if d.estado_erupcion:pieza.estado_erupcion=d.estado_erupcion
    if d.estado_pieza:pieza.estado_pieza=d.estado_pieza
    if d.perdida_prematura is not None:pieza.perdida_prematura=d.perdida_prematura
    if d.numero_pieza_sucesora is not None:pieza.numero_pieza_sucesora=d.numero_pieza_sucesora
    auditar(s,u.clinica_id,u.id,"crear_hallazgo","odontograma","hallazgos_dentales",numero,nuevos=d.model_dump(mode="json"));s.commit();return {**dic(x),"condicion":pieza.condicion,"estado_tratamiento":pieza.estado_tratamiento}
@router.get("/odontogramas/{id_}/piezas/{numero}/historial")
def historial_pieza(id_:int,numero:int,u:Usuario=Depends(exigir_permiso("odontograma")),s:Session=Depends(obtener_sesion)):
    propio(s,Odontograma,id_,u.clinica_id);pieza=s.scalar(select(PiezaOdontograma).where(PiezaOdontograma.odontograma_id==id_,PiezaOdontograma.numero_pieza==numero));return [dic(x) for x in s.scalars(select(HallazgoDental).where(HallazgoDental.pieza_odontograma_id==pieza.id).order_by(HallazgoDental.fecha_registro.desc()))] if pieza else []
@router.put("/hallazgos-dentales/{id_}")
def editar_hallazgo(id_:int,d:HallazgoActualizar,u:Usuario=Depends(exigir_permiso("odontograma","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=s.scalar(select(HallazgoDental).join(PiezaOdontograma).join(Odontograma).where(HallazgoDental.id==id_,Odontograma.clinica_id==u.clinica_id))
    if not x:raise HTTPException(404,"Hallazgo no encontrado")
    # Conserva el hallazgo previo y crea una evolución nueva.
    nuevo=HallazgoDental(pieza_odontograma_id=x.pieza_odontograma_id,odontologo_id=u.id,superficie_dental=x.superficie_dental,diagnostico=x.diagnostico,tratamiento_indicado=d.tratamiento_indicado or x.tratamiento_indicado,estado=d.estado or x.estado,observaciones=d.observaciones or x.observaciones);s.add(nuevo);s.commit();return dic(nuevo)
@router.patch("/hallazgos-dentales/{id_}/estado")
def estado_hallazgo(id_:int,d:HallazgoActualizar,u:Usuario=Depends(exigir_permiso("odontograma","puede_editar")),s:Session=Depends(obtener_sesion)):return editar_hallazgo(id_,d,u,s)

# Agenda
def validar_cruce(s,u,inicio,fin,odontologo_id,consultorio_id,excluir=None):
    if fin<=inicio:raise HTTPException(422,"La hora de fin debe ser posterior a la hora de inicio")
    base=[Cita.clinica_id==u.clinica_id,Cita.estado.notin_(("cancelada","no_asistio")),Cita.fecha_hora_inicio<fin,Cita.fecha_hora_fin>inicio]
    if excluir:base.append(Cita.id!=excluir)
    if s.scalar(select(Cita.id).where(*base,Cita.odontologo_id==odontologo_id)):raise HTTPException(409,"El odontólogo ya tiene una cita en ese horario")
    if consultorio_id and s.scalar(select(Cita.id).where(*base,Cita.consultorio_id==consultorio_id)):raise HTTPException(409,"El consultorio ya está ocupado en ese horario")
def cita_enriquecida(s,x):
    p=s.get(Paciente,x.paciente_id);o=s.get(Usuario,x.odontologo_id);se=s.get(Sede,x.sede_id);co=s.get(Consultorio,x.consultorio_id) if x.consultorio_id else None
    plan=s.get(PlanTratamiento,x.plan_tratamiento_id) if x.plan_tratamiento_id else None;responsable=s.get(Usuario,plan.odontologo_id) if plan else None;sesion=s.scalar(select(SesionTratamiento).where(SesionTratamiento.cita_id==x.id).order_by(SesionTratamiento.id.desc()))
    return {**dic(x),"paciente_nombre":f"{p.nombres} {p.apellidos}","paciente_documento":p.numero_documento,"odontologo_nombre":f"{o.nombres} {o.apellidos}","sede_nombre":se.nombre,"consultorio_nombre":co.nombre if co else None,"plan_numero":plan.numero_plan if plan else None,"tratamiento_relacionado":plan.nombre_tratamiento if plan else None,"odontologo_plan_nombre":f"{responsable.nombres} {responsable.apellidos}" if responsable else None,"sesion_id":sesion.id if sesion else None,"sesion_estado":sesion.estado if sesion else None}
def validar_consultorio(s,u,sede_id,consultorio_id):
    if consultorio_id and not s.scalar(select(Consultorio.id).where(Consultorio.id==consultorio_id,Consultorio.clinica_id==u.clinica_id,Consultorio.sede_id==sede_id,Consultorio.estado==True)):raise HTTPException(422,"El consultorio no pertenece a la sede seleccionada")
def validar_plan_cita(s,u,paciente_id,plan_id):
    if not plan_id:return None
    plan=propio(s,PlanTratamiento,plan_id,u.clinica_id)
    if plan.estado not in ("aprobado","activo"):raise HTTPException(409,"Solo puede vincular citas a planes aprobados o activos")
    if plan.paciente_id!=paciente_id:raise HTTPException(422,"El plan seleccionado no pertenece al paciente de la cita")
    return plan
@router.get("/consultorios")
def consultorios(sede_id:int|None=None,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    q=select(Consultorio).where(Consultorio.clinica_id==u.clinica_id);q=q.where(Consultorio.sede_id==sede_id) if sede_id else q;return [dic(x) for x in s.scalars(q)]
@router.post("/consultorios",status_code=201)
def crear_consultorio(sede_id:int,nombre:str,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_crear")),s:Session=Depends(obtener_sesion)):
    if not s.scalar(select(Sede.id).where(Sede.id==sede_id,Sede.clinica_id==u.clinica_id)):raise HTTPException(400,"Sede inválida")
    x=Consultorio(clinica_id=u.clinica_id,sede_id=sede_id,nombre=nombre);s.add(x);s.commit();return dic(x)
@router.get("/tipos-cita")
def tipos_cita(u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):return [dic(x) for x in s.scalars(select(TipoCita).where(TipoCita.clinica_id==u.clinica_id))]
@router.post("/tipos-cita",status_code=201)
def crear_tipo_cita(nombre:str,duracion_minutos:int=30,color:str="#10a88f",u:Usuario=Depends(exigir_permiso("agenda_citas","puede_crear")),s:Session=Depends(obtener_sesion)):
    x=TipoCita(clinica_id=u.clinica_id,nombre=nombre,duracion_minutos=duracion_minutos,color=color);s.add(x);s.commit();return dic(x)
@router.get("/citas/agenda/diaria")
def agenda_diaria(fecha:date,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    inicio=datetime.combine(fecha,time.min).replace(tzinfo=timezone.utc);fin=inicio+timedelta(days=1);return [dic(x) for x in s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=inicio,Cita.fecha_hora_inicio<fin).order_by(Cita.fecha_hora_inicio))]
@router.get("/citas/agenda/semanal")
def agenda_semanal(fecha:date,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    lunes=fecha-timedelta(days=fecha.weekday());inicio=datetime.combine(lunes,time.min).replace(tzinfo=timezone.utc);fin=inicio+timedelta(days=7);return [dic(x) for x in s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=inicio,Cita.fecha_hora_inicio<fin).order_by(Cita.fecha_hora_inicio))]
def rango_dia(fecha:date):
    inicio=datetime.combine(fecha,time.min).replace(tzinfo=timezone.utc);return inicio,inicio+timedelta(days=1)
def render_recordatorio(s,c,plantilla,mensaje=None):
    p=s.get(Paciente,c.paciente_id);o=s.get(Usuario,c.odontologo_id);se=s.get(Sede,c.sede_id);texto=mensaje or (plantilla.contenido if plantilla else "")
    if not texto:raise HTTPException(422,"Debe indicar mensaje o plantilla")
    datos={"paciente":f"{p.nombres} {p.apellidos}","fecha":c.fecha_hora_inicio.date().isoformat(),"hora":c.fecha_hora_inicio.strftime("%H:%M"),"odontologo":f"{o.nombres} {o.apellidos}","sede":se.nombre,"motivo":c.motivo}
    for k,v in datos.items():texto=texto.replace("{"+k+"}",str(v))
    return texto,p
def contar_estados(citas):
    return {e:sum(1 for c in citas if c.estado==e) for e in ("programada","confirmada","en_atencion","atendida","cancelada","no_asistio")}
@router.get("/agenda/panel")
def panel_agenda(fecha:date|None=None,dias_proximas:int=7,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    ref=fecha or date.today();hoy_ini,hoy_fin=rango_dia(ref);prox_fin=hoy_fin+timedelta(days=dias_proximas);mes_ini=datetime(ref.year,ref.month,1,tzinfo=timezone.utc);mes_fin=(datetime(ref.year+1,1,1,tzinfo=timezone.utc) if ref.month==12 else datetime(ref.year,ref.month+1,1,tzinfo=timezone.utc))
    citas_hoy=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=hoy_ini,Cita.fecha_hora_inicio<hoy_fin).order_by(Cita.fecha_hora_inicio)))
    proximas=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=hoy_fin,Cita.fecha_hora_inicio<prox_fin,Cita.estado.in_(("programada","confirmada","en_atencion"))).order_by(Cita.fecha_hora_inicio).limit(12)))
    pendientes=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=hoy_ini,Cita.estado=="programada").order_by(Cita.fecha_hora_inicio).limit(12)))
    no_asistieron=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.estado=="no_asistio").order_by(Cita.fecha_hora_inicio.desc()).limit(12)))
    mes=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=mes_ini,Cita.fecha_hora_inicio<mes_fin)))
    odontologos={}
    for c in mes:
        o=s.get(Usuario,c.odontologo_id);k=c.odontologo_id;odontologos.setdefault(k,{"odontologo_id":k,"odontologo_nombre":f"{o.nombres} {o.apellidos}","total":0,**{e:0 for e in ("programada","confirmada","en_atencion","atendida","cancelada","no_asistio")}});odontologos[k]["total"]+=1;odontologos[k][c.estado]=odontologos[k].get(c.estado,0)+1
    pendientes_recordatorio=s.scalar(select(func.count(RecordatorioCita.id)).where(RecordatorioCita.clinica_id==u.clinica_id,RecordatorioCita.estado=="pendiente")) or 0
    return {"fecha":ref.isoformat(),"citas_hoy":[cita_enriquecida(s,c) for c in citas_hoy],"proximas_citas":[cita_enriquecida(s,c) for c in proximas],"pendientes_confirmacion":[cita_enriquecida(s,c) for c in pendientes],"pacientes_no_asistieron":[cita_enriquecida(s,c) for c in no_asistieron],"indicadores_odontologo":list(odontologos.values()),"reporte_estados":contar_estados(mes),"recordatorios_pendientes":pendientes_recordatorio}
@router.get("/plantillas-recordatorio")
def listar_plantillas_recordatorio(activo:bool|None=None,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    q=select(PlantillaRecordatorio).where(PlantillaRecordatorio.clinica_id==u.clinica_id)
    if activo is not None:q=q.where(PlantillaRecordatorio.activo==activo)
    return [dic(x) for x in s.scalars(q.order_by(PlantillaRecordatorio.nombre))]
@router.post("/plantillas-recordatorio",status_code=201)
def crear_plantilla_recordatorio(d:PlantillaRecordatorioCrear,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_crear")),s:Session=Depends(obtener_sesion)):
    x=PlantillaRecordatorio(clinica_id=u.clinica_id,**d.model_dump());s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"crear_plantilla_recordatorio","agenda_citas","plantillas_recordatorio",x.id,nuevos=d.model_dump());s.commit();return dic(x)
@router.put("/plantillas-recordatorio/{id_}")
def editar_plantilla_recordatorio(id_:int,d:PlantillaRecordatorioActualizar,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlantillaRecordatorio,id_,u.clinica_id);antes=dic(x);asignar(x,d.model_dump(exclude_unset=True));auditar(s,u.clinica_id,u.id,"editar_plantilla_recordatorio","agenda_citas","plantillas_recordatorio",x.id,antes,d.model_dump(exclude_unset=True));s.commit();return dic(x)
@router.get("/citas/{id_}/recordatorios")
def recordatorios_cita(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    propio(s,Cita,id_,u.clinica_id);return [dic(x) for x in s.scalars(select(RecordatorioCita).where(RecordatorioCita.clinica_id==u.clinica_id,RecordatorioCita.cita_id==id_).order_by(RecordatorioCita.fecha_creacion.desc()))]
@router.post("/citas/{id_}/recordatorios",status_code=201)
def crear_recordatorio_cita(id_:int,d:RecordatorioCitaCrear,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_crear")),s:Session=Depends(obtener_sesion)):
    c=propio(s,Cita,id_,u.clinica_id);plantilla=propio(s,PlantillaRecordatorio,d.plantilla_id,u.clinica_id) if d.plantilla_id else None;mensaje,p=render_recordatorio(s,c,plantilla,d.mensaje);estado=d.estado;fecha_envio=datetime.now(timezone.utc) if estado=="enviado" else None
    x=RecordatorioCita(clinica_id=u.clinica_id,cita_id=c.id,paciente_id=c.paciente_id,plantilla_id=d.plantilla_id,canal=d.canal,destinatario=d.destinatario or p.telefono or p.correo,mensaje=mensaje,estado=estado,fecha_programada=d.fecha_programada,fecha_envio=fecha_envio,usuario_envio_id=u.id if estado=="enviado" else None,observaciones=d.observaciones);s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"registrar_recordatorio","agenda_citas","recordatorios_cita",x.id,nuevos=d.model_dump(mode="json"));s.commit();return dic(x)
@router.patch("/recordatorios-cita/{id_}/marcar-enviado")
def marcar_recordatorio_enviado(id_:int,d:MarcarRecordatorioEnviado=MarcarRecordatorioEnviado(),u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,RecordatorioCita,id_,u.clinica_id)
    if x.estado=="cancelado":raise HTTPException(409,"No se puede enviar un recordatorio cancelado")
    x.estado="enviado";x.fecha_envio=datetime.now(timezone.utc);x.usuario_envio_id=u.id;x.observaciones=d.observaciones or x.observaciones;auditar(s,u.clinica_id,u.id,"marcar_recordatorio_enviado","agenda_citas","recordatorios_cita",x.id);s.commit();return dic(x)
@router.patch("/citas/{id_}/confirmar-rapido")
def confirmar_rapido(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id)
    if x.estado!="programada":raise HTTPException(409,"Solo una cita programada puede confirmarse")
    x.estado="confirmada";auditar(s,u.clinica_id,u.id,"confirmar_rapido","agenda_citas","citas",x.id);s.commit();return dic(x)
@router.get("/citas/fecha/{fecha}/pdf")
def pdf_agenda_diaria(fecha:date,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    inicio,fin=rango_dia(fecha);xs=list(s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=inicio,Cita.fecha_hora_inicio<fin).order_by(Cita.fecha_hora_inicio)))
    lineas=[f"{c.fecha_hora_inicio.strftime('%H:%M')} - {c.fecha_hora_fin.strftime('%H:%M')} | {s.get(Paciente,c.paciente_id).nombres} {s.get(Paciente,c.paciente_id).apellidos} | {c.tipo_cita} | {c.estado}" for c in xs]
    return Response(pdf_basico(f"Agenda diaria {fecha.isoformat()}",lineas or ["Sin citas registradas"]),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="agenda-{fecha.isoformat()}.pdf"'})
@router.get("/citas/paciente/{paciente_id}")
def citas_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [cita_enriquecida(s,x) for x in s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.paciente_id==paciente_id).order_by(Cita.fecha_hora_inicio.desc()))]
@router.get("/citas/plan/{plan_id}")
def citas_plan(plan_id:int,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    propio(s,PlanTratamiento,plan_id,u.clinica_id);return [cita_enriquecida(s,x) for x in s.scalars(select(Cita).where(Cita.clinica_id==u.clinica_id,Cita.plan_tratamiento_id==plan_id).order_by(Cita.fecha_hora_inicio.desc()))]
@router.get("/citas")
def citas(fecha_desde:datetime|None=None,fecha_hasta:datetime|None=None,sede_id:int|None=None,odontologo_id:int|None=None,estado:str|None=None,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    f=[Cita.clinica_id==u.clinica_id]
    if fecha_desde:f.append(Cita.fecha_hora_inicio>=fecha_desde)
    if fecha_hasta:f.append(Cita.fecha_hora_inicio<=fecha_hasta)
    if sede_id:f.append(Cita.sede_id==sede_id)
    if odontologo_id:f.append(Cita.odontologo_id==odontologo_id)
    if estado:f.append(Cita.estado==estado)
    return [cita_enriquecida(s,x) for x in s.scalars(select(Cita).where(*f).order_by(Cita.fecha_hora_inicio))]
@router.get("/citas/fecha/{fecha}")
def citas_fecha(fecha:date,sede_id:int|None=None,odontologo_id:int|None=None,estado:str|None=None,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):
    inicio=datetime.combine(fecha,time.min).replace(tzinfo=timezone.utc);fin=inicio+timedelta(days=1);f=[Cita.clinica_id==u.clinica_id,Cita.fecha_hora_inicio>=inicio,Cita.fecha_hora_inicio<fin]
    if sede_id:f.append(Cita.sede_id==sede_id)
    if odontologo_id:f.append(Cita.odontologo_id==odontologo_id)
    if estado:f.append(Cita.estado==estado)
    return [cita_enriquecida(s,x) for x in s.scalars(select(Cita).where(*f).order_by(Cita.fecha_hora_inicio))]
@router.post("/citas",status_code=201)
def crear_cita(d:CitaCrear,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_crear")),s:Session=Depends(obtener_sesion)):
    validar_relaciones(s,u,d.paciente_id,d.sede_id,d.odontologo_id);validar_plan_cita(s,u,d.paciente_id,d.plan_tratamiento_id);validar_consultorio(s,u,d.sede_id,d.consultorio_id);validar_cruce(s,u,d.fecha_hora_inicio,d.fecha_hora_fin,d.odontologo_id,d.consultorio_id);x=Cita(clinica_id=u.clinica_id,**d.model_dump());s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"crear","agenda_citas","citas",x.id,nuevos=d.model_dump(mode="json"));s.commit();return cita_enriquecida(s,x)
@router.get("/citas/{id_}")
def cita(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas")),s:Session=Depends(obtener_sesion)):return cita_enriquecida(s,propio(s,Cita,id_,u.clinica_id))
@router.put("/citas/{id_}")
def editar_cita(id_:int,d:CitaActualizar,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id);validar_relaciones(s,u,d.paciente_id,d.sede_id,d.odontologo_id);validar_plan_cita(s,u,d.paciente_id,d.plan_tratamiento_id);validar_consultorio(s,u,d.sede_id,d.consultorio_id);validar_cruce(s,u,d.fecha_hora_inicio,d.fecha_hora_fin,d.odontologo_id,d.consultorio_id,id_);antes=dic(x);asignar(x,d.model_dump());auditar(s,u.clinica_id,u.id,"editar","agenda_citas","citas",x.id,antes,d.model_dump(mode="json"));s.commit();return cita_enriquecida(s,x)
@router.patch("/citas/{id_}/confirmar")
def confirmar_cita(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id)
    if x.estado!="programada":raise HTTPException(409,"Solo una cita programada puede confirmarse")
    x.estado="confirmada";auditar(s,u.clinica_id,u.id,"confirmar","agenda_citas","citas",x.id);s.commit();return dic(x)
@router.patch("/citas/{id_}/cancelar")
def cancelar_cita(id_:int,d:MotivoCambio,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id)
    if x.estado in ("atendida","cancelada","no_asistio"):raise HTTPException(409,"La cita ya tiene un estado final")
    x.estado="cancelada";x.motivo_cambio=d.motivo;auditar(s,u.clinica_id,u.id,"cancelar","agenda_citas","citas",x.id,nuevos={"motivo":d.motivo});s.commit();return dic(x)
@router.patch("/citas/{id_}/reprogramar")
def reprogramar_cita(id_:int,d:ReprogramarCita,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id);validar_cruce(s,u,d.fecha_hora_inicio,d.fecha_hora_fin,x.odontologo_id,x.consultorio_id,id_);x.fecha_hora_inicio=d.fecha_hora_inicio;x.fecha_hora_fin=d.fecha_hora_fin;x.estado="reprogramada";x.motivo_cambio=d.motivo;auditar(s,u.clinica_id,u.id,"reprogramar","agenda_citas","citas",x.id,nuevos=d.model_dump(mode="json"));s.commit();return dic(x)
@router.patch("/citas/{id_}/atendida")
@router.patch("/citas/{id_}/marcar-atendida",include_in_schema=False)
def atender_cita(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id)
    if x.estado=="cancelada":raise HTTPException(409,"Una cita cancelada no puede marcarse como atendida")
    if x.estado in ("atendida","no_asistio"):raise HTTPException(409,"La cita ya tiene un estado final")
    x.estado="atendida";auditar(s,u.clinica_id,u.id,"atender","agenda_citas","citas",x.id);s.commit();return dic(x)
@router.patch("/citas/{id_}/no-asistio")
def no_asistio_cita(id_:int,u:Usuario=Depends(exigir_permiso("agenda_citas","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cita,id_,u.clinica_id)
    if x.estado in ("atendida","cancelada","no_asistio"):raise HTTPException(409,"La cita ya tiene un estado final")
    x.estado="no_asistio";auditar(s,u.clinica_id,u.id,"no_asistio","agenda_citas","citas",x.id);s.commit();return dic(x)

# Cotizaciones
def calcular_detalle(d):
    bruto=(Decimal(d.cantidad)*Decimal(d.precio_unitario)).quantize(Decimal("0.01"));descuento=(bruto*Decimal(d.descuento_porcentaje)/100).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP);return bruto,descuento,bruto-descuento
def recalcular_cotizacion(s,x):
    ds=list(s.scalars(select(DetalleCotizacion).where(DetalleCotizacion.cotizacion_id==x.id)));x.subtotal=sum((d.precio_unitario*d.cantidad for d in ds),Decimal(0));x.descuento_total=sum((d.descuento_monto for d in ds),Decimal(0));x.total_estimado=x.subtotal-x.descuento_total;x.cuota_mensual_propuesta=((x.total_estimado-x.pago_inicial_propuesto)/x.numero_cuotas_propuesto).quantize(Decimal("0.01")) if x.numero_cuotas_propuesto else 0
def asegurar_editable(x):
    if x.estado=="convertida":raise HTTPException(409,"No se puede modificar una cotización convertida")
@router.get("/cotizaciones")
def cotizaciones(paciente_id:int|None=None,estado:str|None=None,u:Usuario=Depends(exigir_permiso("cotizaciones")),s:Session=Depends(obtener_sesion)):
    f=[Cotizacion.clinica_id==u.clinica_id]
    if paciente_id:f.append(Cotizacion.paciente_id==paciente_id)
    if estado:f.append(Cotizacion.estado==estado)
    return [dic(x) for x in s.scalars(select(Cotizacion).where(*f).order_by(Cotizacion.fecha_creacion.desc()))]
@router.post("/cotizaciones",status_code=201)
def crear_cotizacion(d:CotizacionCrear,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_crear")),s:Session=Depends(obtener_sesion)):
    validar_relaciones(s,u,d.paciente_id,d.sede_id,d.odontologo_id);datos=d.model_dump(exclude={"detalles"});x=Cotizacion(clinica_id=u.clinica_id,numero_cotizacion=correlativo(s,Cotizacion,u.clinica_id,"COT"),**datos);s.add(x);s.flush()
    for item in d.detalles:
        bruto,desc,sub=calcular_detalle(item);s.add(DetalleCotizacion(cotizacion_id=x.id,descuento_monto=desc,subtotal=sub,**item.model_dump()))
    s.flush();recalcular_cotizacion(s,x);auditar(s,u.clinica_id,u.id,"crear","cotizaciones","cotizaciones",x.id);s.commit();return dic(x)
@router.get("/cotizaciones/{id_}")
def cotizacion(id_:int,u:Usuario=Depends(exigir_permiso("cotizaciones")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);return {**dic(x),"detalles":[dic(d) for d in s.scalars(select(DetalleCotizacion).where(DetalleCotizacion.cotizacion_id==id_).order_by(DetalleCotizacion.orden))]}
@router.put("/cotizaciones/{id_}")
def editar_cotizacion(id_:int,d:CotizacionActualizar,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);asegurar_editable(x);asignar(x,d.model_dump(exclude_unset=True));recalcular_cotizacion(s,x);auditar(s,u.clinica_id,u.id,"editar","cotizaciones","cotizaciones",x.id);s.commit();return dic(x)
@router.post("/cotizaciones/{id_}/detalles",status_code=201)
def agregar_detalle(id_:int,d:DetalleCotizacionCrear,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);asegurar_editable(x);bruto,desc,sub=calcular_detalle(d);z=DetalleCotizacion(cotizacion_id=id_,descuento_monto=desc,subtotal=sub,**d.model_dump());s.add(z);s.flush();recalcular_cotizacion(s,x);s.commit();return dic(z)
@router.put("/cotizaciones/{id_}/detalles/{detalle_id}")
def editar_detalle(id_:int,detalle_id:int,d:DetalleCotizacionCrear,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);asegurar_editable(x);z=s.scalar(select(DetalleCotizacion).where(DetalleCotizacion.id==detalle_id,DetalleCotizacion.cotizacion_id==id_));
    if not z:raise HTTPException(404,"Detalle no encontrado")
    bruto,desc,sub=calcular_detalle(d);asignar(z,d.model_dump());z.descuento_monto=desc;z.subtotal=sub;recalcular_cotizacion(s,x);s.commit();return dic(z)
@router.delete("/cotizaciones/{id_}/detalles/{detalle_id}")
def eliminar_detalle(id_:int,detalle_id:int,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_eliminar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);asegurar_editable(x);z=s.scalar(select(DetalleCotizacion).where(DetalleCotizacion.id==detalle_id,DetalleCotizacion.cotizacion_id==id_));
    if not z:raise HTTPException(404,"Detalle no encontrado")
    s.delete(z);s.flush();recalcular_cotizacion(s,x);s.commit();return {"mensaje":"Detalle eliminado"}
@router.patch("/cotizaciones/{id_}/estado")
def estado_cotizacion(id_:int,d:EstadoCotizacion,u:Usuario=Depends(exigir_permiso("cotizaciones","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);asegurar_editable(x);x.estado=d.estado;auditar(s,u.clinica_id,u.id,d.estado,"cotizaciones","cotizaciones",x.id);s.commit();return dic(x)
def pdf_basico(titulo,lineas):
    texto=" | ".join([titulo,*lineas]).replace("(","[").replace(",",")")[:1200];stream=f"BT /F1 12 Tf 50 780 Td ({texto}) Tj ET";objetos=["<< /Type /Catalog /Pages 2 0 R >>","<< /Type /Pages /Kids [3 0 R] /Count 1 >>","<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];pdf="%PDF-1.4\n";offs=[0]
    for i,o in enumerate(objetos,1):offs.append(len(pdf));pdf+=f"{i} 0 obj\n{o}\nendobj\n"
    xref=len(pdf);pdf+=f"xref\n0 6\n0000000000 65535 f \n"+"".join(f"{x:010d} 00000 n \n" for x in offs[1:])+f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF";return pdf.encode("latin-1","replace")
@router.post("/cotizaciones/{id_}/generar-pdf")
def generar_pdf(id_:int,u:Usuario=Depends(exigir_permiso("cotizaciones")),s:Session=Depends(obtener_sesion)):
    x=propio(s,Cotizacion,id_,u.clinica_id);return Response(pdf_basico(f"Cotizacion {x.numero_cotizacion}",[f"Total: {x.total_estimado}"]),media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{x.numero_cotizacion}.pdf"'})

# Planes
def recalcular_plan(s,x):
    ds=list(s.scalars(select(DetallePlanTratamiento).where(DetallePlanTratamiento.plan_tratamiento_id==x.id)));x.costo_total_estimado=sum((d.costo_estimado for d in ds),Decimal(0));total=sum((d.cantidad_sesiones for d in ds),0);hechas=sum((min(d.sesiones_completadas,d.cantidad_sesiones) for d in ds),0);x.avance_porcentaje=(Decimal(hechas)*100/total).quantize(Decimal("0.01")) if total else 0
@router.post("/cotizaciones/{id_}/convertir-plan",status_code=201)
def convertir_plan(id_:int,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_crear")),s:Session=Depends(obtener_sesion)):
    c=propio(s,Cotizacion,id_,u.clinica_id)
    if c.estado!="aceptada":raise HTTPException(409,"Solo una cotización aceptada puede convertirse")
    if s.scalar(select(PlanTratamiento.id).where(PlanTratamiento.cotizacion_id==id_)):raise HTTPException(409,"La cotización ya fue convertida")
    detalles_cot=list(s.scalars(select(DetalleCotizacion).where(DetalleCotizacion.cotizacion_id==c.id)));p=PlanTratamiento(clinica_id=u.clinica_id,sede_id=c.sede_id,paciente_id=c.paciente_id,odontologo_id=c.odontologo_id,cotizacion_id=c.id,numero_plan=correlativo(s,PlanTratamiento,u.clinica_id,"PLAN"),nombre_tratamiento=detalles_cot[0].procedimiento if detalles_cot else c.diagnostico_resumen,diagnostico_principal=c.diagnostico_resumen,costo_total_estimado=c.total_estimado);s.add(p);s.flush()
    for d in detalles_cot:
        z=DetallePlanTratamiento(plan_tratamiento_id=p.id,procedimiento=d.procedimiento,descripcion=d.descripcion,pieza_dental=d.pieza_dental,tipo_alcance="pieza" if d.pieza_dental else "general",cantidad_sesiones=max(d.cantidad,1),costo_estimado=d.subtotal,orden=d.orden);s.add(z);s.flush()
        if d.pieza_dental:s.add(DetallePlanPieza(detalle_plan_tratamiento_id=z.id,numero_pieza=d.pieza_dental,rol_pieza="asociada"))
    c.estado="convertida";auditar(s,u.clinica_id,u.id,"convertir","cotizaciones","cotizaciones",c.id,nuevos={"plan_id":p.id});auditar(s,u.clinica_id,u.id,"crear","planes_tratamiento","planes_tratamiento",p.id);s.commit();return dic(p)
@router.get("/planes-tratamiento/paciente/{paciente_id}")
def planes_paciente(paciente_id:int,u:Usuario=Depends(exigir_permiso("planes_tratamiento")),s:Session=Depends(obtener_sesion)):paciente_propio(s,paciente_id,u.clinica_id);return [dic(x) for x in s.scalars(select(PlanTratamiento).where(PlanTratamiento.clinica_id==u.clinica_id,PlanTratamiento.paciente_id==paciente_id))]
def plan_enriquecido(s:Session,x:PlanTratamiento,detalle=False):
    paciente=s.get(Paciente,x.paciente_id);odontologo=s.get(Usuario,x.odontologo_id);ds=list(s.scalars(select(DetallePlanTratamiento).where(DetallePlanTratamiento.plan_tratamiento_id==x.id).order_by(DetallePlanTratamiento.orden)));realizadas=sum(d.sesiones_completadas for d in ds);estimadas=sum(d.cantidad_sesiones for d in ds);proxima=s.scalar(select(func.min(SesionTratamiento.fecha_hora_inicio)).where(SesionTratamiento.plan_tratamiento_id==x.id,SesionTratamiento.estado.in_(("programada","reprogramada")),SesionTratamiento.fecha_hora_inicio>=datetime.now(timezone.utc)));base={**dic(x),"paciente_nombre":f"{paciente.nombres} {paciente.apellidos}","paciente_documento":paciente.numero_documento,"odontologo_nombre":f"{odontologo.nombres} {odontologo.apellidos}","tratamiento_resumen":x.nombre_tratamiento or (ds[0].procedimiento if ds else "Sin procedimientos"),"sesiones_realizadas":realizadas,"sesiones_pendientes":max(0,estimadas-realizadas),"proxima_sesion":proxima}
    if detalle:base["detalles"]=[{**dic(d),"piezas":[dic(p) for p in s.scalars(select(DetallePlanPieza).where(DetallePlanPieza.detalle_plan_tratamiento_id==d.id))]} for d in ds]
    return base
@router.get("/planes-tratamiento")
def planes(u:Usuario=Depends(exigir_permiso("planes_tratamiento")),s:Session=Depends(obtener_sesion)):return [plan_enriquecido(s,x) for x in s.scalars(select(PlanTratamiento).where(PlanTratamiento.clinica_id==u.clinica_id).order_by(PlanTratamiento.fecha_creacion.desc()))]
@router.post("/planes-tratamiento",status_code=201)
def crear_plan(d:PlanCrear,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_crear")),s:Session=Depends(obtener_sesion)):
    validar_relaciones(s,u,d.paciente_id,d.sede_id,d.odontologo_id);x=PlanTratamiento(clinica_id=u.clinica_id,numero_plan=correlativo(s,PlanTratamiento,u.clinica_id,"PLAN"),**d.model_dump());s.add(x);s.flush();auditar(s,u.clinica_id,u.id,"crear","planes_tratamiento","planes_tratamiento",x.id);s.commit();return dic(x)
@router.get("/planes-tratamiento/{id_}")
def plan(id_:int,u:Usuario=Depends(exigir_permiso("planes_tratamiento")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);return plan_enriquecido(s,x,True)
@router.put("/planes-tratamiento/{id_}")
def editar_plan(id_:int,d:PlanActualizar,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);asignar(x,d.model_dump(exclude_unset=True));s.commit();return dic(x)
@router.post("/planes-tratamiento/{id_}/detalles",status_code=201)
def agregar_detalle_plan(id_:int,d:DetallePlanCrear,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);datos=d.model_dump(exclude={"piezas"});piezas=d.piezas
    if d.tipo_alcance=="pieza" and not piezas and d.pieza_dental:piezas=[PiezaPlanCrear(numero_pieza=d.pieza_dental)]
    if d.tipo_alcance not in ("pieza","varias_piezas"):datos["pieza_dental"]=None
    elif d.tipo_alcance=="pieza":datos["pieza_dental"]=piezas[0].numero_pieza
    z=DetallePlanTratamiento(plan_tratamiento_id=id_,**datos);s.add(z);s.flush();[s.add(DetallePlanPieza(detalle_plan_tratamiento_id=z.id,**p.model_dump())) for p in piezas];recalcular_plan(s,x)
    if not x.nombre_tratamiento:x.nombre_tratamiento=z.procedimiento
    auditar(s,u.clinica_id,u.id,"agregar_procedimiento","planes_tratamiento","detalles_plan_tratamiento",z.id);s.commit();return {**dic(z),"piezas":[p.model_dump() for p in piezas]}
@router.put("/planes-tratamiento/{id_}/detalles/{detalle_id}")
def editar_detalle_plan(id_:int,detalle_id:int,d:DetallePlanCrear,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);z=s.scalar(select(DetallePlanTratamiento).where(DetallePlanTratamiento.id==detalle_id,DetallePlanTratamiento.plan_tratamiento_id==id_));
    if not z:raise HTTPException(404,"Detalle no encontrado")
    datos=d.model_dump(exclude={"piezas"});asignar(z,datos);s.execute(delete(DetallePlanPieza).where(DetallePlanPieza.detalle_plan_tratamiento_id==z.id));[s.add(DetallePlanPieza(detalle_plan_tratamiento_id=z.id,**p.model_dump())) for p in d.piezas];recalcular_plan(s,x);s.commit();return dic(z)
@router.patch("/planes-tratamiento/{id_}/estado")
def estado_plan(id_:int,d:EstadoPlan,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);x.estado=d.estado;auditar(s,u.clinica_id,u.id,"cambiar_estado","planes_tratamiento","planes_tratamiento",x.id,nuevos={"estado":d.estado});s.commit();return dic(x)
@router.patch("/planes-tratamiento/{id_}/aprobar")
def aprobar_plan(id_:int,d:AprobarPlan,u:Usuario=Depends(exigir_permiso("planes_tratamiento","puede_editar")),s:Session=Depends(obtener_sesion)):
    x=propio(s,PlanTratamiento,id_,u.clinica_id);x.estado="aprobado";x.fecha_aprobacion=datetime.now(timezone.utc);x.observacion_aceptacion=d.observacion;auditar(s,u.clinica_id,u.id,"aprobar","planes_tratamiento","planes_tratamiento",x.id);s.commit();return dic(x)
