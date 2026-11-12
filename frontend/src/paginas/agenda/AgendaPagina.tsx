import { useEffect, useState, type FormEvent } from "react";
import { Bell, ChevronLeft, ChevronRight, Download, Plus, Send } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import api from "../../servicios/api";
import { Encabezado, ErrorCarga, Modal } from "../operaciones/Comun";
import {
  AgendaDiaria,
  AgendaMensual,
  AgendaSemanal,
  DetalleCita,
  type CitaAgenda,
} from "./ComponentesAgenda";
const tipos = [
    "evaluacion_inicial",
    "control",
    "procedimiento",
    "urgencia",
    "revision",
    "ortodoncia",
    "profilaxis",
    "blanqueamiento",
    "otro",
  ],
  estados = ["programada", "confirmada", "atendida", "cancelada", "no_asistio"];
const iso = (d: Date) =>
    new Date(d.getTime() - d.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10),
  hoy = () => iso(new Date());
const vacio = {
  paciente_id: "",
  plan_tratamiento_id: "",
  sede_id: "",
  odontologo_id: "",
  consultorio_id: "",
  fecha: hoy(),
  hora_inicio: "09:00",
  hora_fin: "09:30",
  tipo_cita: "evaluacion_inicial",
  motivo: "",
  observaciones: "",
  estado: "programada",
};
type Vista = "dia" | "semana" | "mes";
function rango(fecha: string, vista: Vista) {
  const d = new Date(`${fecha}T12:00`),
    inicio = new Date(d),
    fin = new Date(d);
  if (vista === "semana") {
    inicio.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    fin.setTime(inicio.getTime());
    fin.setDate(inicio.getDate() + 7);
  } else if (vista === "mes") {
    inicio.setDate(1);
    fin.setMonth(inicio.getMonth() + 1, 1);
  } else fin.setDate(d.getDate() + 1);
  return { inicio, fin };
}
export default function Agenda() {
  const [citas, setCitas] = useState<CitaAgenda[]>([]),
    [pacientes, setPacientes] = useState<any[]>([]),
    [planes, setPlanes] = useState<any[]>([]),
    [sedes, setSedes] = useState<any[]>([]),
    [odontologos, setOdontologos] = useState<any[]>([]),
    [consultorios, setConsultorios] = useState<any[]>([]);
  const [panel, setPanel] = useState<any>(),
    [plantillas, setPlantillas] = useState<any[]>([]),
    [citaRecordatorio, setCitaRecordatorio] = useState<CitaAgenda>(),
    [recordatorios, setRecordatorios] = useState<any[]>([]),
    [recordatorioForm, setRecordatorioForm] = useState({
      plantilla_id: "",
      canal: "whatsapp",
      estado: "pendiente",
      destinatario: "",
      mensaje: "",
      fecha_programada: "",
      observaciones: "",
    }),
    [plantillaForm, setPlantillaForm] = useState({
      nombre: "",
      canal: "whatsapp",
      contenido:
        "Hola {paciente}, le recordamos su cita odontológica el {fecha} a las {hora} en {sede}.",
    });
  const [fecha, setFecha] = useState(hoy()),
    [vista, setVista] = useState<Vista>("dia"),
    [filtro, setFiltro] = useState({
      sede_id: "",
      odontologo_id: "",
      estado: "",
    }),
    [modal, setModal] = useState(false),
    [seleccionada, setSeleccionada] = useState<CitaAgenda>(),
    [citaSesion, setCitaSesion] = useState<CitaAgenda>(),
    [planSesion, setPlanSesion] = useState<any>(),
    [sesionForm, setSesionForm] = useState({
      detalle_plan_tratamiento_id: "",
      pieza_dental: "",
      observaciones: "",
    }),
    [form, setForm] = useState<any>(vacio),
    [editando, setEditando] = useState<number>(),
    [error, setError] = useState(""),
    [cargando, setCargando] = useState(true),
    [params] = useSearchParams();
  async function cargar() {
    setCargando(true);
    setError("");
    try {
      const { inicio, fin } = rango(fecha, vista),
        query: any = {
          fecha_desde: inicio.toISOString(),
          fecha_hasta: fin.toISOString(),
          ...Object.fromEntries(Object.entries(filtro).filter(([, v]) => v)),
        };
      const [r, p, s, u, pl, pa, pr] = await Promise.all([
        api.get("/citas", { params: query }),
        api.get("/pacientes", { params: { limite: 100 } }),
        api.get("/sedes"),
        api.get("/usuarios"),
        api.get("/planes-tratamiento"),
        api.get("/agenda/panel", { params: { fecha } }),
        api.get("/plantillas-recordatorio", { params: { activo: true } }),
      ]);
      setCitas(r.data);
      setPacientes(p.data.datos);
      setSedes(s.data);
      setOdontologos(Array.isArray(u.data) ? u.data : u.data.datos || []);
      setPlanes(pl.data);
      setPanel(pa.data);
      setPlantillas(pr.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo cargar la agenda");
    } finally {
      setCargando(false);
    }
  }
  useEffect(() => {
    cargar();
  }, [fecha, vista, filtro.sede_id, filtro.odontologo_id, filtro.estado]);
  useEffect(() => {
    if (!planes.length) return;
    const plan = planes.find((x) => x.id === Number(params.get("plan"))),
      paciente = params.get("paciente");
    if (plan || paciente) {
      setForm({
        ...vacio,
        fecha,
        paciente_id: String(plan?.paciente_id || paciente),
        plan_tratamiento_id: plan ? String(plan.id) : "",
        odontologo_id: plan ? String(plan.odontologo_id) : "",
        sede_id: plan ? String(plan.sede_id) : "",
      });
      setModal(true);
    }
  }, [planes.length]);
  function mover(n: number) {
    const d = new Date(`${fecha}T12:00`);
    vista === "dia"
      ? d.setDate(d.getDate() + n)
      : vista === "semana"
        ? d.setDate(d.getDate() + 7 * n)
        : d.setMonth(d.getMonth() + n);
    setFecha(iso(d));
  }
  async function sede(v: string) {
    setForm({ ...form, sede_id: v, consultorio_id: "" });
    setConsultorios(
      v
        ? (await api.get("/consultorios", { params: { sede_id: v } })).data
        : [],
    );
  }
  function nueva(dia = fecha) {
    setEditando(undefined);
    setForm({ ...vacio, fecha: dia });
    setModal(true);
  }
  function elegirPaciente(v: string) {
    setForm({ ...form, paciente_id: v, plan_tratamiento_id: "" });
  }
  function elegirPlan(v: string) {
    const p = planes.find((x) => x.id === Number(v));
    setForm({
      ...form,
      plan_tratamiento_id: v,
      paciente_id: p ? String(p.paciente_id) : form.paciente_id,
      odontologo_id: p ? String(p.odontologo_id) : form.odontologo_id,
      sede_id: p ? String(p.sede_id) : form.sede_id,
    });
  }
  async function editar(c: CitaAgenda) {
    setSeleccionada(undefined);
    setEditando(c.id);
    setForm({
      paciente_id: String(c.paciente_id),
      plan_tratamiento_id: c.plan_tratamiento_id
        ? String(c.plan_tratamiento_id)
        : "",
      sede_id: String(c.sede_id),
      odontologo_id: String(c.odontologo_id),
      consultorio_id: c.consultorio_id ? String(c.consultorio_id) : "",
      fecha: c.fecha_hora_inicio.slice(0, 10),
      hora_inicio: c.fecha_hora_inicio.slice(11, 16),
      hora_fin: c.fecha_hora_fin.slice(11, 16),
      tipo_cita: c.tipo_cita,
      motivo: c.motivo,
      observaciones: c.observaciones || "",
      estado: c.estado,
    });
    setConsultorios(
      (await api.get("/consultorios", { params: { sede_id: c.sede_id } })).data,
    );
    setModal(true);
  }
  async function guardar(e: FormEvent) {
    e.preventDefault();
    const d = {
      paciente_id: Number(form.paciente_id),
      plan_tratamiento_id: Number(form.plan_tratamiento_id) || null,
      sede_id: Number(form.sede_id),
      odontologo_id: Number(form.odontologo_id),
      consultorio_id: Number(form.consultorio_id) || null,
      tipo_cita: form.tipo_cita,
      motivo: form.motivo,
      observaciones: form.observaciones || null,
      estado: form.estado,
      fecha_hora_inicio: new Date(
        `${form.fecha}T${form.hora_inicio}:00`,
      ).toISOString(),
      fecha_hora_fin: new Date(
        `${form.fecha}T${form.hora_fin}:00`,
      ).toISOString(),
    };
    try {
      editando
        ? await api.put(`/citas/${editando}`, d)
        : await api.post("/citas", d);
      setModal(false);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo guardar la cita");
    }
  }
  async function accion(c: CitaAgenda, a: string) {
    try {
      if (a === "cancelar") {
        const motivo = prompt("Motivo de cancelación");
        if (!motivo) return;
        await api.patch(`/citas/${c.id}/cancelar`, { motivo });
      } else await api.patch(`/citas/${c.id}/${a}`);
      setSeleccionada(undefined);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo cambiar el estado");
    }
  }
  async function confirmarRapido(c: CitaAgenda) {
    try {
      await api.patch(`/citas/${c.id}/confirmar-rapido`);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo confirmar la cita");
    }
  }
  async function exportarPdf() {
    const r = await api.get(`/citas/fecha/${fecha}/pdf`, { responseType: "blob" });
    window.open(URL.createObjectURL(r.data));
  }
  async function abrirRecordatorios(c: CitaAgenda) {
    setCitaRecordatorio(c);
    setRecordatorios((await api.get(`/citas/${c.id}/recordatorios`)).data);
    setRecordatorioForm({
      plantilla_id: "",
      canal: "whatsapp",
      estado: "pendiente",
      destinatario: "",
      mensaje: "",
      fecha_programada: "",
      observaciones: "",
    });
  }
  async function crearRecordatorio(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/citas/${citaRecordatorio!.id}/recordatorios`, {
        plantilla_id: Number(recordatorioForm.plantilla_id) || null,
        canal: recordatorioForm.canal,
        estado: recordatorioForm.estado,
        destinatario: recordatorioForm.destinatario || null,
        mensaje: recordatorioForm.mensaje || null,
        fecha_programada: recordatorioForm.fecha_programada
          ? new Date(recordatorioForm.fecha_programada).toISOString()
          : null,
        observaciones: recordatorioForm.observaciones || null,
      });
      abrirRecordatorios(citaRecordatorio!);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo registrar el recordatorio");
    }
  }
  async function marcarEnviado(id: number) {
    await api.patch(`/recordatorios-cita/${id}/marcar-enviado`, {});
    abrirRecordatorios(citaRecordatorio!);
    cargar();
  }
  async function crearPlantilla(e: FormEvent) {
    e.preventDefault();
    await api.post("/plantillas-recordatorio", plantillaForm);
    const r = await api.get("/plantillas-recordatorio", { params: { activo: true } });
    setPlantillas(r.data);
    setPlantillaForm({
      nombre: "",
      canal: "whatsapp",
      contenido:
        "Hola {paciente}, le recordamos su cita odontológica el {fecha} a las {hora} en {sede}.",
    });
  }
  async function abrirSesion(c: CitaAgenda) {
    const plan = (await api.get(`/planes-tratamiento/${c.plan_tratamiento_id}`))
      .data;
    setPlanSesion(plan);
    setCitaSesion(c);
    setSeleccionada(undefined);
    setSesionForm({
      detalle_plan_tratamiento_id: "",
      pieza_dental: "",
      observaciones: "",
    });
  }
  async function registrarSesion(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post(`/citas/${citaSesion!.id}/sesion`, {
        detalle_plan_tratamiento_id: Number(
          sesionForm.detalle_plan_tratamiento_id,
        ),
        pieza_dental: Number(sesionForm.pieza_dental) || null,
        observaciones: sesionForm.observaciones || null,
      });
      setCitaSesion(undefined);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo registrar la sesiÃ³n");
    }
  }
  const planActual = planes.find(
      (x) => x.id === Number(form.plan_tratamiento_id),
    ),
    pacienteActual = pacientes.find((x) => x.id === Number(form.paciente_id));
  return (
    <>
      <Encabezado
        titulo="Agenda y citas"
        subtitulo="Agenda integrada con pacientes y planes de tratamiento."
        accion={
          <button className="boton" onClick={() => nueva()}>
            <Plus />
            Nueva cita
          </button>
        }
      />
      <div className="tarjeta mt-5 flex flex-wrap items-end gap-3">
        <div className="flex rounded-xl bg-slate-100 p-1">
          {(["dia", "semana", "mes"] as Vista[]).map((v) => (
            <button
              key={v}
              onClick={() => setVista(v)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${vista === v ? "bg-white text-marca-700 shadow-sm" : "text-slate-500"}`}
            >
              {v === "dia" ? "Día" : v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <button className="boton-sec" onClick={() => setFecha(hoy())}>
          Hoy
        </button>
        <div className="flex">
          <button
            aria-label="Anterior"
            className="boton-sec rounded-r-none"
            onClick={() => mover(-1)}
          >
            <ChevronLeft />
          </button>
          <button
            aria-label="Siguiente"
            className="boton-sec rounded-l-none border-l-0"
            onClick={() => mover(1)}
          >
            <ChevronRight />
          </button>
        </div>
        <label>
          <span className="etiqueta">Fecha</span>
          <input
            className="campo"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
        </label>
        <Select
          label="Sede"
          value={filtro.sede_id}
          set={(v) => setFiltro({ ...filtro, sede_id: v })}
          data={sedes.map((x) => [x.id, x.nombre])}
          libre
        />
        <Select
          label="Odontólogo"
          value={filtro.odontologo_id}
          set={(v) => setFiltro({ ...filtro, odontologo_id: v })}
          data={odontologos.map((x) => [x.id, `${x.nombres} ${x.apellidos}`])}
          libre
        />
        <Select
          label="Estado"
          value={filtro.estado}
          set={(v) => setFiltro({ ...filtro, estado: v })}
          data={estados.map((x) => [x, x.replaceAll("_", " ")])}
          libre
        />
        <button className="boton-sec" onClick={exportarPdf}>
          <Download size={16} />
          Exportar PDF diario
        </button>
      </div>
      {panel && (
        <PanelSeguimiento
          panel={panel}
          abrir={setSeleccionada}
          confirmar={confirmarRapido}
        />
      )}
      <ErrorCarga cargando={cargando} error={error} />
      {vista === "dia" && (
        <AgendaDiaria fecha={fecha} citas={citas} abrir={setSeleccionada} />
      )}{" "}
      {vista === "semana" && (
        <AgendaSemanal fecha={fecha} citas={citas} abrir={setSeleccionada} />
      )}{" "}
      {vista === "mes" && (
        <AgendaMensual
          fecha={fecha}
          citas={citas}
          abrir={setSeleccionada}
          seleccionarDia={(d) => {
            setFecha(d);
            setVista("dia");
          }}
        />
      )}
      <DetalleCita
        cita={seleccionada}
        cerrar={() => setSeleccionada(undefined)}
        editar={editar}
        accion={accion}
        registrarSesion={abrirSesion}
        abrirRecordatorios={abrirRecordatorios}
      />
      {citaRecordatorio && (
        <Modal
          titulo={`Recordatorios · ${citaRecordatorio.paciente_nombre}`}
          cerrar={() => setCitaRecordatorio(undefined)}
          ancho="max-w-3xl"
        >
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
            <div className="space-y-4">
            <form onSubmit={crearPlantilla} className="rounded-2xl border p-4">
              <h3 className="font-bold">Plantillas de recordatorio</h3>
              <p className="mb-3 text-sm text-slate-500">
                Variables disponibles: {"{paciente}"}, {"{fecha}"}, {"{hora}"}, {"{odontologo}"}, {"{sede}"}, {"{motivo}"}.
              </p>
              <label className="block"><span className="etiqueta">Nombre</span><input required className="campo" value={plantillaForm.nombre} onChange={(e)=>setPlantillaForm({...plantillaForm,nombre:e.target.value})} placeholder="Recordatorio 24 horas"/></label>
              <Select label="Canal" value={plantillaForm.canal} set={(v)=>setPlantillaForm({...plantillaForm,canal:v})} data={["interno","whatsapp","sms","email"].map((x)=>[x,x])}/>
              <label className="mt-3 block"><span className="etiqueta">Contenido</span><textarea required className="campo" value={plantillaForm.contenido} onChange={(e)=>setPlantillaForm({...plantillaForm,contenido:e.target.value})}/></label>
              <button className="boton-sec mt-3 w-full">Crear plantilla</button>
            </form>
            <form onSubmit={crearRecordatorio} className="rounded-2xl bg-slate-50 p-4">
              <h3 className="font-bold">Registrar recordatorio</h3>
              <p className="mb-3 text-sm text-slate-500">
                WhatsApp queda solo como registro preparado; no se envía fuera del sistema.
              </p>
              <Select label="Plantilla" value={recordatorioForm.plantilla_id} set={(v)=>setRecordatorioForm({...recordatorioForm,plantilla_id:v,mensaje:""})} data={plantillas.map((p)=>[p.id,p.nombre])} libre/>
              <Select label="Canal" value={recordatorioForm.canal} set={(v)=>setRecordatorioForm({...recordatorioForm,canal:v})} data={["interno","whatsapp","sms","email"].map((x)=>[x,x])}/>
              <Select label="Estado" value={recordatorioForm.estado} set={(v)=>setRecordatorioForm({...recordatorioForm,estado:v})} data={["pendiente","enviado"].map((x)=>[x,x])}/>
              <label className="mt-3 block"><span className="etiqueta">Destinatario</span><input className="campo" value={recordatorioForm.destinatario} onChange={(e)=>setRecordatorioForm({...recordatorioForm,destinatario:e.target.value})} placeholder="Teléfono, correo o referencia interna"/></label>
              {!recordatorioForm.plantilla_id&&<label className="mt-3 block"><span className="etiqueta">Mensaje</span><textarea required className="campo" value={recordatorioForm.mensaje} onChange={(e)=>setRecordatorioForm({...recordatorioForm,mensaje:e.target.value})}/></label>}
              <label className="mt-3 block"><span className="etiqueta">Fecha programada</span><input className="campo" type="datetime-local" value={recordatorioForm.fecha_programada} onChange={(e)=>setRecordatorioForm({...recordatorioForm,fecha_programada:e.target.value})}/></label>
              <label className="mt-3 block"><span className="etiqueta">Observación</span><input className="campo" value={recordatorioForm.observaciones} onChange={(e)=>setRecordatorioForm({...recordatorioForm,observaciones:e.target.value})}/></label>
              <button className="boton mt-4 w-full"><Bell size={16}/>Guardar recordatorio</button>
            </form>
            </div>
            <div>
              <h3 className="font-bold">Historial de recordatorios</h3>
              <div className="mt-3 grid gap-2">
                {recordatorios.map((r)=>(
                  <div className="rounded-xl border p-3 text-sm" key={r.id}>
                    <div className="flex justify-between gap-3"><b className="capitalize">{r.canal}</b><span className="rounded-full bg-slate-100 px-2 text-xs capitalize">{r.estado}</span></div>
                    <p className="mt-2 text-slate-600">{r.mensaje}</p>
                    <small>{r.destinatario || "Sin destinatario"} · {r.fecha_envio ? new Date(r.fecha_envio).toLocaleString() : "Pendiente"}</small>
                    {r.estado==="pendiente"&&<button className="boton-sec mt-3 w-full" onClick={()=>marcarEnviado(r.id)}><Send size={15}/>Marcar enviado</button>}
                  </div>
                ))}
                {!recordatorios.length&&<p className="rounded-xl bg-slate-50 p-6 text-center text-slate-500">Aún no hay recordatorios registrados.</p>}
              </div>
            </div>
          </div>
        </Modal>
      )}
      {citaSesion && planSesion && (
        <Modal
          titulo="Registrar sesiÃ³n desde cita"
          cerrar={() => setCitaSesion(undefined)}
        >
          <form onSubmit={registrarSesion} className="grid gap-3 md:grid-cols-2">
            <div className="md:col-span-2 rounded-xl bg-marca-50 p-4">
              <b>{citaSesion.paciente_nombre}</b>
              <p>{planSesion.nombre_tratamiento}</p>
              <small>
                {new Date(citaSesion.fecha_hora_inicio).toLocaleString()} Â· {citaSesion.odontologo_nombre}
              </small>
            </div>
            <Select
              label="Procedimiento"
              value={sesionForm.detalle_plan_tratamiento_id}
              set={(v) =>
                setSesionForm({
                  ...sesionForm,
                  detalle_plan_tratamiento_id: v,
                  pieza_dental: "",
                })
              }
              data={planSesion.detalles
                .filter((d: any) =>
                  ["pendiente", "en_progreso"].includes(d.estado),
                )
                .map((d: any) => [
                  d.id,
                  `${d.procedimiento} Â· ${d.tipo_alcance.replaceAll("_", " ")}`,
                ])}
            />
            {(() => {
              const d = planSesion.detalles.find(
                (x: any) =>
                  x.id === Number(sesionForm.detalle_plan_tratamiento_id),
              );
              if (!d || !["pieza", "varias_piezas"].includes(d.tipo_alcance))
                return null;
              return (
                <Select
                  label="Pieza vinculada"
                  value={sesionForm.pieza_dental}
                  set={(v) => setSesionForm({ ...sesionForm, pieza_dental: v })}
                  data={(d.piezas?.length
                    ? d.piezas
                    : d.pieza_dental
                      ? [{ numero_pieza: d.pieza_dental, rol_pieza: "asociada" }]
                      : []
                  ).map((p: any) => [
                    p.numero_pieza,
                    `${p.numero_pieza} Â· ${p.rol_pieza}`,
                  ])}
                />
              );
            })()}
            <label className="md:col-span-2">
              <span className="etiqueta">Observaciones iniciales</span>
              <textarea
                className="campo"
                value={sesionForm.observaciones}
                onChange={(e) =>
                  setSesionForm({
                    ...sesionForm,
                    observaciones: e.target.value,
                  })
                }
              />
            </label>
            <button className="boton md:col-span-2">Crear sesiÃ³n clÃ­nica</button>
          </form>
        </Modal>
      )}
      {modal && (
        <Modal
          titulo={editando ? "Editar cita" : "Nueva cita"}
          cerrar={() => setModal(false)}
        >
          <form onSubmit={guardar} className="grid gap-3 md:grid-cols-2">
            <Select
              label="Paciente"
              value={form.paciente_id}
              set={elegirPaciente}
              data={pacientes.map((x) => [
                x.id,
                `${x.nombres} ${x.apellidos} · ${x.numero_documento || "sin documento"}`,
              ])}
            />
            <Select
              label="Plan de tratamiento (opcional)"
              value={form.plan_tratamiento_id}
              set={elegirPlan}
              data={planes
                .filter(
                  (p) =>
                    ["aprobado", "activo"].includes(p.estado) &&
                    (!form.paciente_id ||
                      p.paciente_id === Number(form.paciente_id)),
                )
                .map((p) => [
                  p.id,
                  `${p.numero_plan} · ${p.nombre_tratamiento || p.tratamiento_resumen}`,
                ])}
              libre
            />
            {pacienteActual && (
              <div className="md:col-span-2 rounded-xl bg-marca-50 p-4">
                <b>
                  {pacienteActual.nombres} {pacienteActual.apellidos}
                </b>
                <p>
                  {planActual
                    ? planActual.nombre_tratamiento ||
                      planActual.tratamiento_resumen
                    : "Cita independiente"}
                </p>
                {planActual && (
                  <small>
                    Odontólogo responsable: {planActual.odontologo_nombre}
                  </small>
                )}
              </div>
            )}
            <Select
              label="Sede"
              value={form.sede_id}
              set={sede}
              data={sedes.map((x) => [x.id, x.nombre])}
            />
            <Select
              label="Odontólogo"
              value={form.odontologo_id}
              set={(v) => setForm({ ...form, odontologo_id: v })}
              data={odontologos.map((x) => [
                x.id,
                `${x.nombres} ${x.apellidos}`,
              ])}
            />
            <Select
              label="Consultorio (opcional)"
              value={form.consultorio_id}
              set={(v) => setForm({ ...form, consultorio_id: v })}
              data={consultorios.map((x) => [x.id, x.nombre])}
              libre
            />
            <label>
              <span className="etiqueta">Fecha</span>
              <input
                required
                className="campo"
                type="date"
                value={form.fecha}
                onChange={(e) => setForm({ ...form, fecha: e.target.value })}
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label>
                <span className="etiqueta">Inicio</span>
                <input
                  required
                  className="campo"
                  type="time"
                  value={form.hora_inicio}
                  onChange={(e) =>
                    setForm({ ...form, hora_inicio: e.target.value })
                  }
                />
              </label>
              <label>
                <span className="etiqueta">Fin</span>
                <input
                  required
                  className="campo"
                  type="time"
                  value={form.hora_fin}
                  onChange={(e) =>
                    setForm({ ...form, hora_fin: e.target.value })
                  }
                />
              </label>
            </div>
            <Select
              label="Tipo"
              value={form.tipo_cita}
              set={(v) => setForm({ ...form, tipo_cita: v })}
              data={tipos.map((x) => [x, x.replaceAll("_", " ")])}
            />
            <Select
              label="Estado"
              value={form.estado}
              set={(v) => setForm({ ...form, estado: v })}
              data={estados.map((x) => [x, x.replaceAll("_", " ")])}
            />
            <label className="md:col-span-2">
              <span className="etiqueta">Motivo</span>
              <input
                required
                minLength={3}
                className="campo"
                value={form.motivo}
                onChange={(e) => setForm({ ...form, motivo: e.target.value })}
              />
            </label>
            <label className="md:col-span-2">
              <span className="etiqueta">Observaciones</span>
              <textarea
                className="campo"
                value={form.observaciones}
                onChange={(e) =>
                  setForm({ ...form, observaciones: e.target.value })
                }
              />
            </label>
            <button className="boton md:col-span-2">Guardar cita</button>
          </form>
        </Modal>
      )}
    </>
  );
}
function Select({
  label,
  value,
  set,
  data,
  libre = false,
}: {
  label: string;
  value: any;
  set: (v: string) => void;
  data: any[];
  libre?: boolean;
}) {
  return (
    <label className="min-w-36">
      <span className="etiqueta">{label}</span>
      <select
        required={!libre}
        className="campo"
        value={value}
        onChange={(e) => set(e.target.value)}
      >
        <option value="">{libre ? "Ninguno / todos" : "Seleccione"}</option>
        {data.map(([v, n]) => (
          <option key={v} value={v}>
            {n}
          </option>
        ))}
      </select>
    </label>
  );
}
function PanelSeguimiento({
  panel,
  abrir,
  confirmar,
}: {
  panel: any;
  abrir: (c: CitaAgenda) => void;
  confirmar: (c: CitaAgenda) => void;
}) {
  const estados = panel.reporte_estados || {};
  return (
    <div className="mt-5 grid gap-4 xl:grid-cols-[1.3fr_.9fr]">
      <div className="tarjeta">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">Citas de hoy</h2>
            <p className="text-sm text-slate-500">
              Seguimiento operativo, confirmaciones y recordatorios.
            </p>
          </div>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-700">
            {panel.recordatorios_pendientes} recordatorios pendientes
          </span>
        </div>
        <div className="mt-4 grid gap-2">
          {panel.citas_hoy?.slice(0, 6).map((c: CitaAgenda) => (
            <div
              key={c.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3 text-sm"
            >
              <button className="text-left" onClick={() => abrir(c)}>
                <b>{new Date(c.fecha_hora_inicio).toLocaleTimeString("es-PE",{hour:"2-digit",minute:"2-digit"})} · {c.paciente_nombre}</b>
                <p className="text-slate-500">{c.tipo_cita.replaceAll("_"," ")} · {c.estado.replaceAll("_"," ")}</p>
              </button>
              {c.estado === "programada" && (
                <button className="boton-sec" onClick={() => confirmar(c)}>
                  Confirmación rápida
                </button>
              )}
            </div>
          ))}
          {!panel.citas_hoy?.length && (
            <p className="rounded-xl bg-slate-50 p-6 text-center text-slate-500">
              No hay citas para hoy.
            </p>
          )}
        </div>
      </div>
      <div className="grid gap-4">
        <div className="grid grid-cols-3 gap-2">
          <Mini n="Atendidas" v={estados.atendida || 0} />
          <Mini n="Canceladas" v={estados.cancelada || 0} />
          <Mini n="No asistió" v={estados.no_asistio || 0} />
        </div>
        <ListaSeguimiento titulo="Próximas citas" datos={panel.proximas_citas} abrir={abrir} />
        <ListaSeguimiento titulo="Pendientes de confirmación" datos={panel.pendientes_confirmacion} abrir={abrir} />
        <ListaSeguimiento titulo="Pacientes no asistieron" datos={panel.pacientes_no_asistieron} abrir={abrir} />
      </div>
      <div className="tarjeta xl:col-span-2">
        <h3 className="font-bold">Indicadores por odontólogo</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-slate-500"><th className="p-2">Odontólogo</th><th>Total</th><th>Atendidas</th><th>Canceladas</th><th>No asistió</th></tr></thead>
            <tbody>{panel.indicadores_odontologo?.map((o:any)=><tr className="border-b last:border-0" key={o.odontologo_id}><td className="p-2 font-medium">{o.odontologo_nombre}</td><td>{o.total}</td><td>{o.atendida}</td><td>{o.cancelada}</td><td>{o.no_asistio}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
function Mini({ n, v }: { n: string; v: number }) {
  return <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100"><p className="text-xs text-slate-500">{n}</p><b className="text-2xl">{v}</b></div>;
}
function ListaSeguimiento({ titulo, datos = [], abrir }: { titulo: string; datos: CitaAgenda[]; abrir: (c: CitaAgenda) => void }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
      <h3 className="font-bold">{titulo}</h3>
      <div className="mt-2 grid gap-1">
        {datos.slice(0, 4).map((c) => (
          <button key={c.id} className="rounded-lg p-2 text-left text-sm hover:bg-slate-50" onClick={() => abrir(c)}>
            <b>{c.paciente_nombre}</b>
            <small className="block text-slate-500">{new Date(c.fecha_hora_inicio).toLocaleString("es-PE")} · {c.estado.replaceAll("_", " ")}</small>
          </button>
        ))}
        {!datos.length && <p className="text-sm text-slate-500">Sin registros.</p>}
      </div>
    </div>
  );
}
