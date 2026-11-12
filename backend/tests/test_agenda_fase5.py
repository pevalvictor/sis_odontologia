from datetime import datetime, timedelta, timezone
from test_fase1 import preparar, paciente

def escenario(cliente):
    h,sede=preparar(cliente,"20777777771","agenda5",["pacientes","agenda_citas"])
    p=paciente(cliente,h,"77770001");perfil=cliente.get("/api/autenticacion/mi-perfil",headers=h).json()
    base=datetime.now(timezone.utc).replace(hour=9,minute=0,second=0,microsecond=0)
    cita=cliente.post("/api/citas",headers=h,json={"sede_id":sede["id"],"paciente_id":p["id"],"odontologo_id":perfil["id"],"tipo_cita":"control","fecha_hora_inicio":base.isoformat(),"fecha_hora_fin":(base+timedelta(minutes=30)).isoformat(),"motivo":"Control pediátrico"}).json()
    return h,cita,base

def test_panel_agenda_y_confirmacion_rapida(cliente):
    h,cita,base=escenario(cliente)
    panel=cliente.get("/api/agenda/panel",headers=h,params={"fecha":base.date().isoformat()}).json()
    assert panel["citas_hoy"] and panel["pendientes_confirmacion"]
    r=cliente.patch(f"/api/citas/{cita['id']}/confirmar-rapido",headers=h)
    assert r.status_code==200 and r.json()["estado"]=="confirmada"

def test_plantillas_y_recordatorios_no_envian_integracion_real(cliente):
    h,cita,_=escenario(cliente)
    plantilla=cliente.post("/api/plantillas-recordatorio",headers=h,json={"nombre":"24 horas","canal":"whatsapp","contenido":"Hola {paciente}, cita {fecha} {hora}"}).json()
    r=cliente.post(f"/api/citas/{cita['id']}/recordatorios",headers=h,json={"plantilla_id":plantilla["id"],"canal":"whatsapp","estado":"pendiente"})
    assert r.status_code==201 and "Paciente Prueba" in r.json()["mensaje"] and r.json()["estado"]=="pendiente"
    enviado=cliente.patch(f"/api/recordatorios-cita/{r.json()['id']}/marcar-enviado",headers=h,json={}).json()
    assert enviado["estado"]=="enviado" and enviado["fecha_envio"]

def test_exportacion_pdf_agenda_diaria(cliente):
    h,_,base=escenario(cliente)
    r=cliente.get(f"/api/citas/fecha/{base.date().isoformat()}/pdf",headers=h)
    assert r.status_code==200 and r.headers["content-type"]=="application/pdf"
