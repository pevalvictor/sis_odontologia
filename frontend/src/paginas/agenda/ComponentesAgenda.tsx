import {
  Bell,
  CalendarDays,
  Check,
  Clock3,
  Pencil,
  UserX,
  X,
  XCircle,
} from "lucide-react";
export type CitaAgenda = {
  id: number;
  paciente_id: number;
  sede_id: number;
  odontologo_id: number;
  consultorio_id?: number;
  plan_tratamiento_id?: number;
  paciente_nombre: string;
  paciente_documento?: string;
  odontologo_nombre: string;
  sede_nombre: string;
  consultorio_nombre?: string;
  plan_numero?: string;
  tratamiento_relacionado?: string;
  odontologo_plan_nombre?: string;
  sesion_id?: number;
  sesion_estado?: string;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  tipo_cita: string;
  motivo: string;
  observaciones?: string;
  estado: string;
};
const estilo: any = {
  programada: "border-blue-500 bg-blue-50 text-blue-900",
  confirmada: "border-emerald-500 bg-emerald-50 text-emerald-900",
  atendida: "border-slate-400 bg-slate-100 text-slate-700",
  cancelada: "border-red-500 bg-red-50 text-red-800",
  no_asistio: "border-purple-500 bg-purple-50 text-purple-800",
};
const fechaLocal = (s: string) =>
    new Date(s).toLocaleDateString("es-PE", {
      weekday: "short",
      day: "2-digit",
      month: "short",
    }),
  hora = (s: string) =>
    new Date(s).toLocaleTimeString("es-PE", {
      hour: "2-digit",
      minute: "2-digit",
    }),
  clave = (s: string) => s.slice(0, 10);
function Tarjeta({
  c,
  abrir,
  compacta = false,
}: {
  c: CitaAgenda;
  abrir: (c: CitaAgenda) => void;
  compacta?: boolean;
}) {
  return (
    <button
      onClick={() => abrir(c)}
      className={`w-full rounded-lg border-l-4 p-2 text-left text-xs ${estilo[c.estado] || estilo.programada}`}
    >
      <b>
        {hora(c.fecha_hora_inicio)} {c.paciente_nombre}
      </b>
      {c.tratamiento_relacionado && (
        <p className="truncate font-medium">{c.tratamiento_relacionado}</p>
      )}
      {!compacta && (
        <>
          <p className="truncate">{c.tipo_cita.replaceAll("_", " ")}</p>
          <small className="line-clamp-1">{c.motivo}</small>
        </>
      )}
    </button>
  );
}
const Vacio = ({ texto }: { texto: string }) => (
  <div className="tarjeta mt-5 py-14 text-center text-slate-500">
    <CalendarDays className="mx-auto mb-2" />
    {texto}
  </div>
);
export function AgendaDiaria({
  fecha,
  citas,
  abrir,
}: {
  fecha: string;
  citas: CitaAgenda[];
  abrir: (c: CitaAgenda) => void;
}) {
  if (!citas.length) return <Vacio texto="No existen citas para este día." />;
  return (
    <div className="mt-5 grid gap-3">
      <h2 className="text-lg font-bold capitalize">
        {new Date(`${fecha}T12:00`).toLocaleDateString("es-PE", {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        })}
      </h2>
      {citas.map((c) => (
        <Tarjeta c={c} abrir={abrir} key={c.id} />
      ))}
    </div>
  );
}
export function AgendaSemanal({
  fecha,
  citas,
  abrir,
}: {
  fecha: string;
  citas: CitaAgenda[];
  abrir: (c: CitaAgenda) => void;
}) {
  const base = new Date(`${fecha}T12:00`);
  base.setDate(base.getDate() - ((base.getDay() + 6) % 7));
  const dias = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(base);
    d.setDate(base.getDate() + i);
    return d;
  });
  const horas = Array.from({ length: 12 }, (_, i) => i + 7);
  return (
    <div className="tarjeta mt-5 overflow-x-auto p-0">
      <div className="min-w-[980px]">
        <div className="grid grid-cols-[64px_repeat(7,1fr)] border-b bg-slate-50">
          <div />
          {dias.map((d) => (
            <div
              className="border-l p-3 text-center text-sm font-semibold capitalize"
              key={d.toISOString()}
            >
              {d.toLocaleDateString("es-PE", {
                weekday: "short",
                day: "2-digit",
              })}
            </div>
          ))}
        </div>
        {horas.map((h) => (
          <div
            className="grid min-h-20 grid-cols-[64px_repeat(7,1fr)] border-b last:border-0"
            key={h}
          >
            <div className="p-2 text-xs text-slate-400">
              {String(h).padStart(2, "0")}:00
            </div>
            {dias.map((d) => {
              const k = d.toISOString().slice(0, 10),
                cs = citas.filter(
                  (c) =>
                    clave(c.fecha_hora_inicio) === k &&
                    new Date(c.fecha_hora_inicio).getHours() === h,
                );
              return (
                <div className="space-y-1 border-l p-1" key={k}>
                  {cs.map((c) => (
                    <Tarjeta compacta c={c} abrir={abrir} key={c.id} />
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
export function AgendaMensual({
  fecha,
  citas,
  abrir,
  seleccionarDia,
}: {
  fecha: string;
  citas: CitaAgenda[];
  abrir: (c: CitaAgenda) => void;
  seleccionarDia: (d: string) => void;
}) {
  const ref = new Date(`${fecha}T12:00`),
    primero = new Date(ref.getFullYear(), ref.getMonth(), 1, 12),
    inicio = new Date(primero);
  inicio.setDate(1 - ((primero.getDay() + 6) % 7));
  const dias = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(inicio);
    d.setDate(inicio.getDate() + i);
    return d;
  });
  return (
    <div className="tarjeta mt-5 overflow-x-auto p-0">
      <div className="min-w-[760px]">
        <div className="grid grid-cols-7 bg-slate-50 text-center text-sm font-semibold">
          {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map((x) => (
            <div className="p-3" key={x}>
              {x}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {dias.map((d) => {
            const k = d.toISOString().slice(0, 10),
              cs = citas.filter((c) => clave(c.fecha_hora_inicio) === k),
              fuera = d.getMonth() !== ref.getMonth();
            return (
              <div
                className={`min-h-28 border-t border-r p-2 ${fuera ? "bg-slate-50 text-slate-400" : ""}`}
                key={k}
              >
                <button
                  className="mb-2 flex w-full justify-between"
                  onClick={() => seleccionarDia(k)}
                >
                  <span>{d.getDate()}</span>
                  {cs.length > 0 && (
                    <b className="rounded-full bg-marca-100 px-2 text-xs text-marca-700">
                      {cs.length} cita{cs.length > 1 ? "s" : ""}
                    </b>
                  )}
                </button>
                <div className="space-y-1">
                  {cs.slice(0, 3).map((c) => (
                    <Tarjeta compacta c={c} abrir={abrir} key={c.id} />
                  ))}
                  {cs.length > 3 && <small>+{cs.length - 3} más</small>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
export function DetalleCita({
  cita,
  cerrar,
  editar,
  accion,
  registrarSesion,
  abrirRecordatorios,
}: {
  cita?: CitaAgenda;
  cerrar: () => void;
  editar: (c: CitaAgenda) => void;
  accion: (c: CitaAgenda, a: string) => void;
  registrarSesion: (c: CitaAgenda) => void;
  abrirRecordatorios: (c: CitaAgenda) => void;
}) {
  if (!cita) return null;
  const final = ["atendida", "cancelada", "no_asistio"].includes(cita.estado);
  return (
    <div className="fixed inset-0 z-50 bg-slate-950/30" onClick={cerrar}>
      <aside
        className="ml-auto h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between">
          <div>
            <small className="uppercase text-slate-500">Detalle de cita</small>
            <h2 className="text-2xl font-bold">{cita.paciente_nombre}</h2>
            <p>{cita.paciente_documento || "Sin documento"}</p>
          </div>
          <button aria-label="Cerrar" onClick={cerrar}>
            <X />
          </button>
        </div>
        <span
          className={`mt-5 inline-block rounded-full border-l-4 px-3 py-1 text-sm font-semibold ${estilo[cita.estado]}`}
        >
          {cita.estado.replaceAll("_", " ")}
        </span>
        <dl className="mt-6 grid gap-4 text-sm">
          <Dato n="Tipo de cita" v={cita.tipo_cita.replaceAll("_", " ")} />
          <Dato n="Motivo" v={cita.motivo} />
          {cita.tratamiento_relacionado && (
            <Dato
              n="Plan relacionado"
              v={`${cita.plan_numero} · ${cita.tratamiento_relacionado}`}
            />
          )}
          <Dato n="Odontólogo" v={cita.odontologo_nombre} />
          <Dato
            n="Sede"
            v={`${cita.sede_nombre}${cita.consultorio_nombre ? ` · ${cita.consultorio_nombre}` : ""}`}
          />
          <Dato
            n="Fecha y horario"
            v={`${fechaLocal(cita.fecha_hora_inicio)} · ${hora(cita.fecha_hora_inicio)}–${hora(cita.fecha_hora_fin)}`}
          />
          <Dato
            n="Observaciones"
            v={cita.observaciones || "Sin observaciones"}
          />
        </dl>
        <div className="mt-8 grid gap-2">
          <button className="boton-sec" onClick={() => abrirRecordatorios(cita)}>
            <Bell size={16} />
            Recordatorios
          </button>
          {cita.sesion_id ? (
            <a className="boton" href={`/sesiones?cita=${cita.id}`}>
              Ver sesiÃ³n #{cita.sesion_id} Â· {cita.sesion_estado}
            </a>
          ) : (
            cita.plan_tratamiento_id &&
            ["confirmada", "en_atencion"].includes(cita.estado) && (
              <button className="boton" onClick={() => registrarSesion(cita)}>
                Registrar sesiÃ³n
              </button>
            )
          )}
          <button className="boton-sec" onClick={() => editar(cita)}>
            <Pencil size={16} />
            Editar cita
          </button>
          {!final && (
            <>
              {cita.estado === "programada" && (
                <button
                  className="boton"
                  onClick={() => accion(cita, "confirmar")}
                >
                  <Check size={16} />
                  Confirmar
                </button>
              )}
              <button
                className="boton-sec"
                onClick={() => accion(cita, "atendida")}
              >
                <Clock3 size={16} />
                Marcar atendida
              </button>
              <button
                className="boton-sec"
                onClick={() => accion(cita, "no-asistio")}
              >
                <UserX size={16} />
                No asistió
              </button>
              <button
                className="boton-sec text-red-700"
                onClick={() => accion(cita, "cancelar")}
              >
                <XCircle size={16} />
                Cancelar cita
              </button>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
function Dato({ n, v }: { n: string; v: string }) {
  return (
    <div>
      <dt className="font-semibold text-slate-500">{n}</dt>
      <dd className="mt-1 capitalize text-slate-900">{v}</dd>
    </div>
  );
}
