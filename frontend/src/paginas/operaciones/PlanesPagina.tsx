import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Plus, Stethoscope, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api from "../../servicios/api";
import { Encabezado, ErrorCarga, Estado, Modal } from "./Comun";
const alcances = [
  "pieza",
  "varias_piezas",
  "cuadrante",
  "arcada_superior",
  "arcada_inferior",
  "ambas_arcadas",
  "general",
];
const detalleInicial = {
  procedimiento: "",
  descripcion: "",
  tipo_alcance: "pieza",
  pieza_dental: "",
  cuadrante: "",
  cantidad_sesiones: 1,
  costo_estimado: "",
  orden: 1,
  piezas: [{ numero_pieza: "", rol_pieza: "asociada" }],
};
export default function PlanesPagina() {
  const [x, setX] = useState<any[]>([]),
    [pacientes, setPacientes] = useState<any[]>([]),
    [sedes, setSedes] = useState<any[]>([]),
    [perfil, setPerfil] = useState<any>(),
    [cotizaciones, setCotizaciones] = useState<any[]>([]),
    [detalle, setDetalle] = useState<any>(),
    [nuevo, setNuevo] = useState(false),
    [agregar, setAgregar] = useState(false),
    [filtro, setFiltro] = useState(""),
    [error, setError] = useState(""),
    [cargando, setCargando] = useState(true);
  const [form, setForm] = useState({
      paciente_id: "",
      sede_id: "",
      nombre_tratamiento: "",
      diagnostico_principal: "",
      fecha_inicio_estimada: "",
      fecha_fin_estimada: "",
      duracion_estimada_meses: 1,
    }),
    [proc, setProc] = useState<any>(detalleInicial);
  const nav = useNavigate();
  async function cargar() {
    setCargando(true);
    setError("");
    try {
      const [r, p, s, u, c] = await Promise.all([
        api.get("/planes-tratamiento"),
        api.get("/pacientes", { params: { limite: 100 } }),
        api.get("/sedes"),
        api.get("/autenticacion/mi-perfil"),
        api.get("/cotizaciones", { params: { estado: "aceptada" } }),
      ]);
      setX(r.data);
      setPacientes(p.data.datos);
      setSedes(s.data);
      setPerfil(u.data);
      setCotizaciones(c.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Error al cargar");
    } finally {
      setCargando(false);
    }
  }
  useEffect(() => {
    cargar();
  }, []);
  async function crear(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/planes-tratamiento", {
        ...form,
        paciente_id: Number(form.paciente_id),
        sede_id: Number(form.sede_id),
        odontologo_id: perfil.id,
        fecha_inicio_estimada: form.fecha_inicio_estimada || null,
        fecha_fin_estimada: form.fecha_fin_estimada || null,
      });
      setNuevo(false);
      cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo crear el plan");
    }
  }
  async function convertir(id: number) {
    await api.post(`/cotizaciones/${id}/convertir-plan`);
    setNuevo(false);
    cargar();
  }
  async function ver(id: number) {
    setDetalle((await api.get(`/planes-tratamiento/${id}`)).data);
  }
  async function aprobar() {
    await api.patch(`/planes-tratamiento/${detalle.id}/aprobar`, {
      observacion: "Aprobado por el paciente",
    });
    ver(detalle.id);
    cargar();
  }
  async function guardarProcedimiento(e: FormEvent) {
    e.preventDefault();
    const piezas =
      proc.tipo_alcance === "pieza"
        ? [{ numero_pieza: Number(proc.pieza_dental), rol_pieza: "asociada" }]
        : proc.tipo_alcance === "varias_piezas"
          ? proc.piezas.map((p: any) => ({
              ...p,
              numero_pieza: Number(p.numero_pieza),
            }))
          : [];
    try {
      await api.post(`/planes-tratamiento/${detalle.id}/detalles`, {
        ...proc,
        pieza_dental:
          proc.tipo_alcance === "pieza" ? Number(proc.pieza_dental) : null,
        cuadrante: proc.tipo_alcance === "cuadrante" ? proc.cuadrante : null,
        cantidad_sesiones: Number(proc.cantidad_sesiones),
        costo_estimado: Number(proc.costo_estimado).toFixed(2),
        piezas,
      });
      setAgregar(false);
      setProc(detalleInicial);
      await ver(detalle.id);
      cargar();
    } catch (e: any) {
      setError(
        e.response?.data?.detail || "No se pudo agregar el procedimiento",
      );
    }
  }
  const lista = x.filter((p) => !filtro || p.estado === filtro);
  return (
    <>
      <Encabezado
        titulo="Planes de tratamiento"
        subtitulo="Procedimientos clínicos, alcance dental, sesiones y avance."
        accion={
          <button className="boton" onClick={() => setNuevo(true)}>
            <Plus />
            Nuevo plan
          </button>
        }
      />
      <select
        className="campo mt-5 w-auto"
        value={filtro}
        onChange={(e) => setFiltro(e.target.value)}
      >
        <option value="">Todos los estados</option>
        {[
          "propuesto",
          "aprobado",
          "activo",
          "suspendido",
          "finalizado",
          "cancelado",
        ].map((v) => (
          <option key={v}>{v}</option>
        ))}
      </select>
      <ErrorCarga cargando={cargando} error={error} />
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {lista.map((p) => (
          <button
            className="tarjeta text-left"
            key={p.id}
            onClick={() => ver(p.id)}
          >
            <div className="flex justify-between">
              <div>
                <b>{p.numero_plan}</b>
                <p className="font-medium">
                  {p.nombre_tratamiento ||
                    p.resumen_tratamiento ||
                    "Plan sin nombre"}
                </p>
              </div>
              <Estado valor={p.estado} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              {p.paciente_nombre} · {p.paciente_documento || "Sin documento"} ·{" "}
              {p.odontologo_nombre}
            </p>
            <p className="text-sm">
              {p.diagnostico_principal || "Sin diagnóstico"} · S/{" "}
              {p.costo_total_estimado}
            </p>
            <div className="mt-4 h-2 rounded bg-slate-100">
              <div
                className="h-full rounded bg-marca-500"
                style={{ width: `${p.avance_porcentaje}%` }}
              />
            </div>
            <small>
              {p.avance_porcentaje}% · {p.sesiones_completadas} realizadas /{" "}
              {p.sesiones_pendientes} pendientes
            </small>
          </button>
        ))}
        {!lista.length && !cargando && (
          <div className="tarjeta col-span-full py-12 text-center">
            <Stethoscope className="mx-auto text-slate-300" size={40} />
            <b className="mt-3 block">No existen planes</b>
            <p className="text-slate-500">
              Crea uno o convierte una cotización aceptada.
            </p>
          </div>
        )}
      </div>
      {nuevo && (
        <Modal titulo="Nuevo plan" cerrar={() => setNuevo(false)}>
          <form onSubmit={crear} className="grid gap-3 md:grid-cols-2">
            <Select
              label="Paciente"
              value={form.paciente_id}
              set={(v) => setForm({ ...form, paciente_id: v })}
              data={pacientes.map((p) => [
                p.id,
                `${p.nombres} ${p.apellidos} · ${p.numero_documento || "sin documento"}`,
              ])}
            />
            <Select
              label="Sede"
              value={form.sede_id}
              set={(v) => setForm({ ...form, sede_id: v })}
              data={sedes.map((s) => [s.id, s.nombre])}
            />
            <Campo
              label="Nombre del tratamiento"
              required
              value={form.nombre_tratamiento}
              set={(v) => setForm({ ...form, nombre_tratamiento: v })}
            />
            <label>
              <span className="etiqueta">Diagnóstico principal</span>
              <input
                required
                className="campo"
                value={form.diagnostico_principal}
                onChange={(e) =>
                  setForm({ ...form, diagnostico_principal: e.target.value })
                }
              />
            </label>
            <Campo
              label="Inicio estimado"
              type="date"
              value={form.fecha_inicio_estimada}
              set={(v) => setForm({ ...form, fecha_inicio_estimada: v })}
            />
            <Campo
              label="Fin estimado"
              type="date"
              value={form.fecha_fin_estimada}
              set={(v) => setForm({ ...form, fecha_fin_estimada: v })}
            />
            <button className="boton md:col-span-2">Crear plan</button>
          </form>
          {cotizaciones.length > 0 && (
            <div className="mt-7 border-t pt-5">
              <h3 className="font-bold">Cotizaciones aceptadas</h3>
              {cotizaciones.map((c) => (
                <div
                  className="mt-2 flex justify-between rounded-xl bg-slate-50 p-3"
                  key={c.id}
                >
                  <span>
                    {c.numero_cotizacion} · S/ {c.total_estimado}
                  </span>
                  <button className="boton-sec" onClick={() => convertir(c.id)}>
                    Convertir
                  </button>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
      {detalle && (
        <Modal
          titulo={`${detalle.numero_plan} · ${detalle.nombre_tratamiento || "Plan sin nombre"}`}
          cerrar={() => setDetalle(null)}
        >
          <div className="flex flex-wrap justify-between gap-3">
            <div>
              <b>{detalle.paciente_nombre}</b>
              <p className="text-sm text-slate-500">
                {detalle.paciente_documento || "Sin documento"} ·{" "}
                {detalle.odontologo_nombre}
              </p>
              <p>{detalle.diagnostico_principal}</p>
            </div>
            <div className="text-right">
              <Estado valor={detalle.estado} />
              <b className="block mt-2">S/ {detalle.costo_total_estimado}</b>
            </div>
          </div>
          <div className="mt-5 h-3 rounded bg-slate-100">
            <div
              className="h-full rounded bg-marca-500"
              style={{ width: `${detalle.avance_porcentaje}%` }}
            />
          </div>
          <p className="mt-1 text-sm">
            {detalle.sesiones_completadas} sesiones realizadas ·{" "}
            {detalle.sesiones_pendientes} pendientes · Próxima:{" "}
            {detalle.proxima_sesion
              ? new Date(detalle.proxima_sesion).toLocaleString()
              : "sin programar"}
          </p>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-sm">
              <tbody>
                {detalle.detalles.map((d: any) => (
                  <tr className="border-t" key={d.id}>
                    <td className="py-3">
                      <b>{d.procedimiento}</b>
                      <small className="block capitalize">
                        {d.tipo_alcance.replaceAll("_", " ")}{" "}
                        {d.cuadrante ? `· ${d.cuadrante}` : ""}
                      </small>
                      <small>
                        {d.piezas
                          ?.map(
                            (p: any) => `${p.numero_pieza} (${p.rol_pieza})`,
                          )
                          .join(", ") || "Sin pieza individual"}
                      </small>
                    </td>
                    <td>
                      {d.sesiones_completadas}/{d.cantidad_sesiones}
                    </td>
                    <td>S/ {d.costo_estimado}</td>
                    <td>
                      <Estado valor={d.estado} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <button className="boton-sec" onClick={() => setAgregar(true)}>
              <Plus />
              Agregar procedimiento
            </button>
            {detalle.estado === "propuesto" && (
              <button className="boton" onClick={aprobar}>
                <CheckCircle2 />
                Aprobar plan
              </button>
            )}
            {["aprobado", "activo"].includes(detalle.estado) && (
              <button
                className="boton"
                onClick={() => nav(`/agenda?plan=${detalle.id}`)}
              >
                Programar cita
              </button>
            )}
            <button
              className="boton-sec"
              disabled={!detalle.detalles.length}
              onClick={() => nav(`/sesiones?plan=${detalle.id}`)}
            >
              Registrar sesión
            </button>
          </div>
        </Modal>
      )}
      {agregar && (
        <Modal
          titulo="Agregar procedimiento al plan"
          cerrar={() => setAgregar(false)}
        >
          <form
            onSubmit={guardarProcedimiento}
            className="grid gap-3 md:grid-cols-2"
          >
            <Campo
              label="Procedimiento"
              required
              value={proc.procedimiento}
              set={(v) => setProc({ ...proc, procedimiento: v })}
            />
            <Select
              label="Alcance"
              value={proc.tipo_alcance}
              set={(v) => setProc({ ...proc, tipo_alcance: v })}
              data={alcances.map((x) => [x, x.replaceAll("_", " ")])}
            />
            {proc.tipo_alcance === "pieza" && (
              <Campo
                label="Pieza FDI"
                required
                type="number"
                value={proc.pieza_dental}
                set={(v) => setProc({ ...proc, pieza_dental: v })}
              />
            )}{" "}
            {proc.tipo_alcance === "cuadrante" && (
              <Select
                label="Cuadrante"
                value={proc.cuadrante}
                set={(v) => setProc({ ...proc, cuadrante: v })}
                data={[
                  "superior_derecho",
                  "superior_izquierdo",
                  "inferior_derecho",
                  "inferior_izquierdo",
                ].map((x) => [x, x.replaceAll("_", " ")])}
              />
            )}
            <Campo
              label="Cantidad de sesiones"
              required
              type="number"
              value={proc.cantidad_sesiones}
              set={(v) => setProc({ ...proc, cantidad_sesiones: v })}
            />
            <Campo
              label="Costo estimado"
              required
              type="number"
              value={proc.costo_estimado}
              set={(v) => setProc({ ...proc, costo_estimado: v })}
            />
            {proc.tipo_alcance === "varias_piezas" && (
              <div className="md:col-span-2 rounded-xl bg-slate-50 p-4">
                <b>Piezas vinculadas y rol</b>
                {proc.piezas.map((p: any, i: number) => (
                  <div
                    className="mt-2 grid grid-cols-[1fr_1fr_auto] gap-2"
                    key={i}
                  >
                    <input
                      required
                      type="number"
                      className="campo"
                      placeholder="FDI"
                      value={p.numero_pieza}
                      onChange={(e) =>
                        setProc({
                          ...proc,
                          piezas: proc.piezas.map((z: any, j: number) =>
                            j === i
                              ? { ...z, numero_pieza: e.target.value }
                              : z,
                          ),
                        })
                      }
                    />
                    <select
                      className="campo"
                      value={p.rol_pieza}
                      onChange={(e) =>
                        setProc({
                          ...proc,
                          piezas: proc.piezas.map((z: any, j: number) =>
                            j === i ? { ...z, rol_pieza: e.target.value } : z,
                          ),
                        })
                      }
                    >
                      {["pilar", "pontico", "asociada"].map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() =>
                        setProc({
                          ...proc,
                          piezas: proc.piezas.filter(
                            (_: any, j: number) => j !== i,
                          ),
                        })
                      }
                    >
                      <Trash2 />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="boton-sec mt-3"
                  onClick={() =>
                    setProc({
                      ...proc,
                      piezas: [
                        ...proc.piezas,
                        { numero_pieza: "", rol_pieza: "asociada" },
                      ],
                    })
                  }
                >
                  <Plus />
                  Agregar pieza
                </button>
              </div>
            )}
            <label className="md:col-span-2">
              <span className="etiqueta">Descripción clínica</span>
              <textarea
                className="campo"
                value={proc.descripcion}
                onChange={(e) =>
                  setProc({ ...proc, descripcion: e.target.value })
                }
              />
            </label>
            <button className="boton md:col-span-2">
              Guardar procedimiento
            </button>
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
}: {
  label: string;
  value: any;
  set: (x: string) => void;
  data: any[];
}) {
  return (
    <label>
      <span className="etiqueta">{label}</span>
      <select
        required
        className="campo"
        value={value}
        onChange={(e) => set(e.target.value)}
      >
        <option value="">Seleccione</option>
        {data.map(([v, n]) => (
          <option value={v} key={v}>
            {n}
          </option>
        ))}
      </select>
    </label>
  );
}
function Campo({
  label,
  value,
  set,
  type = "text",
  required = false,
}: {
  label: string;
  value: any;
  set: (x: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label>
      <span className="etiqueta">{label}</span>
      <input
        required={required}
        type={type}
        min={type === "number" ? 1 : undefined}
        step={label.includes("Costo") ? ".01" : undefined}
        className="campo"
        value={value}
        onChange={(e) => set(e.target.value)}
      />
    </label>
  );
}
