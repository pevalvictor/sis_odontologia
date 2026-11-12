import { useEffect, useState, type FormEvent } from "react";
import { Play, Plus, SquareCheckBig } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import api from "../../servicios/api";
import { Encabezado, ErrorCarga, Estado, Modal } from "./Comun";
export default function SesionesPagina() {
  const [x, setX] = useState<any[]>([]),
    [planes, setPlanes] = useState<any[]>([]),
    [sedes, setSedes] = useState<any[]>([]),
    [perfil, setPerfil] = useState<any>(),
    [planActual, setPlanActual] = useState<any>(),
    [modal, setModal] = useState(false),
    [final, setFinal] = useState<any>(),
    [error, setError] = useState(""),
    [cargando, setCargando] = useState(true),
    [params] = useSearchParams(),
    [form, setForm] = useState({
      plan_tratamiento_id: params.get("plan") || "",
      detalle_plan_tratamiento_id: "",
      sede_id: "",
      fecha_hora_inicio: "",
      procedimiento_realizado: "",
      pieza_dental: "",
      observaciones: "",
      indicaciones: "",
      proxima_sesion_fecha: "",
    }),
    [detalles, setDetalles] = useState<any[]>([]);
  async function cargar() {
    setCargando(true);
    setError("");
    try {
      const [r, p, s, u] = await Promise.all([
        api.get("/sesiones-tratamiento"),
        api.get("/planes-tratamiento"),
        api.get("/sedes"),
        api.get("/autenticacion/mi-perfil"),
      ]);
      setX(r.data);
      setPlanes(p.data);
      setSedes(s.data);
      setPerfil(u.data);
      if (params.get("plan")) await seleccionarPlan(params.get("plan")!);
    } catch (e: any) {
      setError(
        e.response?.data?.detail || "No se pudieron cargar las sesiones",
      );
    } finally {
      setCargando(false);
    }
  }
  useEffect(() => {
    cargar();
  }, []);
  async function seleccionarPlan(id: string) {
    setForm((v) => ({
      ...v,
      plan_tratamiento_id: id,
      detalle_plan_tratamiento_id: "",
      procedimiento_realizado: "",
      pieza_dental: "",
    }));
    if (!id) {
      setPlanActual(null);
      setDetalles([]);
      return;
    }
    const p = (await api.get(`/planes-tratamiento/${id}`)).data;
    setPlanActual(p);
    setDetalles(
      p.detalles.filter((d: any) =>
        ["pendiente", "en_progreso"].includes(d.estado),
      ),
    );
  }
  function seleccionarDetalle(id: string) {
    const d = detalles.find((x) => x.id === Number(id)),
      pieza =
        d?.tipo_alcance === "pieza"
          ? String(d.piezas?.[0]?.numero_pieza || d.pieza_dental || "")
          : "";
    setForm((v) => ({
      ...v,
      detalle_plan_tratamiento_id: id,
      procedimiento_realizado: d?.procedimiento || "",
      pieza_dental: pieza,
    }));
  }
  async function crear(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/sesiones-tratamiento", {
        ...form,
        plan_tratamiento_id: Number(form.plan_tratamiento_id),
        detalle_plan_tratamiento_id: Number(form.detalle_plan_tratamiento_id),
        sede_id: Number(form.sede_id),
        paciente_id: planActual.paciente_id,
        odontologo_id: perfil.id,
        pieza_dental: form.pieza_dental ? Number(form.pieza_dental) : null,
        fecha_hora_inicio: new Date(form.fecha_hora_inicio).toISOString(),
        proxima_sesion_fecha: form.proxima_sesion_fecha
          ? new Date(form.proxima_sesion_fecha).toISOString()
          : null,
      });
      setModal(false);
      await cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail || "No se pudo registrar la sesión");
    }
  }
  async function accion(id: number, a: string, body: any = {}) {
    try {
      await api.patch(`/sesiones-tratamiento/${id}/${a}`, body);
      await cargar();
    } catch (e: any) {
      setError(e.response?.data?.detail);
    }
  }
  async function finalizar(e: FormEvent) {
    e.preventDefault();
    await accion(final.id, "finalizar", {
      resultado: final.resultado,
      observaciones: final.observaciones,
      indicaciones: final.indicaciones,
    });
    setFinal(null);
  }
  const seleccionado = detalles.find(
      (d) => d.id === Number(form.detalle_plan_tratamiento_id),
    ),
    requierePieza = ["pieza", "varias_piezas"].includes(
      seleccionado?.tipo_alcance,
    );
  const lista = params.get("cita")
    ? x.filter((s) => s.cita_id === Number(params.get("cita")))
    : x;
  return (
    <>
      <Encabezado
        titulo="Sesiones de tratamiento"
        subtitulo="Ejecución cronológica vinculada a procedimientos pendientes del plan."
        accion={
          <button className="boton" onClick={() => setModal(true)}>
            <Plus />
            Registrar sesión
          </button>
        }
      />
      <ErrorCarga cargando={cargando} error={error} />
      <div className="mt-6 border-l-2 border-marca-200 pl-6">
        {lista.map((s) => (
          <article className="tarjeta relative mb-4" key={s.id}>
            <i className="absolute -left-[34px] top-6 h-4 w-4 rounded-full bg-marca-500" />
            <div className="flex flex-wrap justify-between gap-3">
              <div>
                <b>
                  Sesión #{s.numero_sesion} · {s.procedimiento_realizado}
                  {s.pieza_dental ? ` · pieza ${s.pieza_dental}` : ""}
                </b>
                <p className="text-sm text-slate-500">
                  {new Date(s.fecha_hora_inicio).toLocaleString()} · Plan #
                  {s.plan_tratamiento_id}
                </p>
                {s.consulta_clinica_id && (
                  <p className="text-xs text-marca-700">
                    Consulta clínica #{s.consulta_clinica_id}
                  </p>
                )}
                {s.cita_id && (
                  <p className="text-xs">Cita relacionada #{s.cita_id}</p>
                )}
              </div>
              <Estado valor={s.estado} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {["programada", "reprogramada"].includes(s.estado) && (
                <button
                  className="boton-sec"
                  onClick={() => accion(s.id, "iniciar")}
                >
                  <Play size={15} />
                  Iniciar
                </button>
              )}
              {["programada", "reprogramada", "en_atencion"].includes(
                s.estado,
              ) && (
                <button
                  className="boton"
                  onClick={() =>
                    setFinal({ ...s, resultado: "", indicaciones: "" })
                  }
                >
                  <SquareCheckBig size={15} />
                  Finalizar
                </button>
              )}
              {!["realizada", "cancelada", "anulada"].includes(s.estado) && (
                <button
                  className="boton-sec"
                  onClick={() => {
                    const m = prompt("Motivo de cancelación");
                    if (m) accion(s.id, "cancelar", { motivo: m });
                  }}
                >
                  Cancelar
                </button>
              )}
              {s.estado === "realizada" && (
                <button
                  className="boton-sec"
                  onClick={() => {
                    const m = prompt("Motivo de anulación");
                    if (m) accion(s.id, "anular", { motivo: m });
                  }}
                >
                  Anular
                </button>
              )}
            </div>
          </article>
        ))}
        {!x.length && !cargando && (
          <p className="tarjeta text-center text-slate-500">
            No hay sesiones registradas.
          </p>
        )}
      </div>
      {modal && (
        <Modal titulo="Registrar sesión" cerrar={() => setModal(false)}>
          <form onSubmit={crear} className="grid gap-3 md:grid-cols-2">
            <Select
              label="Plan"
              value={form.plan_tratamiento_id}
              set={seleccionarPlan}
              data={planes
                .filter((p) => !["cancelado", "finalizado"].includes(p.estado))
                .map((p) => [
                  p.id,
                  `${p.numero_plan} · ${p.paciente_nombre} · ${p.nombre_tratamiento || p.resumen_tratamiento}`,
                ])}
            />
            {planActual && (
              <div className="md:col-span-2 rounded-xl bg-marca-50 p-4">
                <b>
                  {planActual.paciente_nombre} ·{" "}
                  {planActual.paciente_documento || "sin documento"}
                </b>
                <p>
                  {planActual.nombre_tratamiento} ·{" "}
                  {planActual.diagnostico_principal}
                </p>
                <small>
                  {planActual.sesiones_completadas} realizadas /{" "}
                  {planActual.sesiones_pendientes} pendientes
                </small>
              </div>
            )}
            <Select
              label="Procedimiento pendiente"
              value={form.detalle_plan_tratamiento_id}
              set={seleccionarDetalle}
              data={detalles.map((d) => [
                d.id,
                `${d.procedimiento} · ${d.tipo_alcance.replaceAll("_", " ")} · ${d.sesiones_completadas}/${d.cantidad_sesiones}`,
              ])}
            />
            <Select
              label="Sede"
              value={form.sede_id}
              set={(v) => setForm({ ...form, sede_id: v })}
              data={sedes.map((s) => [s.id, s.nombre])}
            />
            <label>
              <span className="etiqueta">Fecha y hora</span>
              <input
                required
                type="datetime-local"
                className="campo"
                value={form.fecha_hora_inicio}
                onChange={(e) =>
                  setForm({ ...form, fecha_hora_inicio: e.target.value })
                }
              />
            </label>
            <label>
              <span className="etiqueta">
                Procedimiento (definido por el plan)
              </span>
              <input
                readOnly
                className="campo bg-slate-50"
                value={form.procedimiento_realizado}
              />
            </label>
            {requierePieza && (
              <Select
                label="Pieza vinculada"
                value={form.pieza_dental}
                set={(v) => setForm({ ...form, pieza_dental: v })}
                data={(seleccionado?.piezas || []).map((p: any) => [
                  p.numero_pieza,
                  `${p.numero_pieza} · ${p.rol_pieza}`,
                ])}
              />
            )}
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
            <label>
              <span className="etiqueta">Próxima sesión</span>
              <input
                type="datetime-local"
                className="campo"
                value={form.proxima_sesion_fecha}
                onChange={(e) =>
                  setForm({ ...form, proxima_sesion_fecha: e.target.value })
                }
              />
            </label>
            <button disabled={!detalles.length} className="boton md:col-span-2">
              Guardar sesión
            </button>
            {planActual && !detalles.length && (
              <p className="md:col-span-2 text-sm text-amber-700">
                Este plan no tiene procedimientos pendientes o en progreso.
              </p>
            )}
          </form>
        </Modal>
      )}
      {final && (
        <Modal
          titulo={`Finalizar sesión #${final.numero_sesion}`}
          cerrar={() => setFinal(null)}
          ancho="max-w-xl"
        >
          <form onSubmit={finalizar} className="grid gap-3">
            <label>
              <span className="etiqueta">Resultado</span>
              <textarea
                required
                className="campo"
                value={final.resultado}
                onChange={(e) =>
                  setFinal({ ...final, resultado: e.target.value })
                }
              />
            </label>
            <label>
              <span className="etiqueta">Observaciones</span>
              <textarea
                className="campo"
                value={final.observaciones || ""}
                onChange={(e) =>
                  setFinal({ ...final, observaciones: e.target.value })
                }
              />
            </label>
            <label>
              <span className="etiqueta">Indicaciones</span>
              <textarea
                className="campo"
                value={final.indicaciones || ""}
                onChange={(e) =>
                  setFinal({ ...final, indicaciones: e.target.value })
                }
              />
            </label>
            <button className="boton">Finalizar y actualizar avance</button>
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
