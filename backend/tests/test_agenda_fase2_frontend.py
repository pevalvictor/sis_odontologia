from pathlib import Path
import re

RAIZ=Path(__file__).parents[2]/"frontend"/"src"/"paginas"/"agenda"

def test_existen_las_tres_vistas_y_el_detalle():
 texto=(RAIZ/"ComponentesAgenda.tsx").read_text(encoding="utf-8")
 for componente in ("AgendaDiaria","AgendaSemanal","AgendaMensual","DetalleCita"):
  assert f"function {componente}" in texto

def test_colores_visuales_por_estado():
 texto=(RAIZ/"ComponentesAgenda.tsx").read_text(encoding="utf-8")
 esperados={"programada":"blue","confirmada":"emerald","atendida":"slate","cancelada":"red","no_asistio":"purple"}
 for estado,color in esperados.items():assert re.search(rf'{estado}["\']?\s*:\s*["\']border-{color}',texto)

def test_navegacion_y_filtros_se_conservan():
 texto=(RAIZ/"AgendaPagina.tsx").read_text(encoding="utf-8")
 for control in ('type Vista = "dia" | "semana" | "mes"',"Hoy","Sede","Odontólogo","Estado","fecha_desde","fecha_hasta"):
  assert control in texto

def test_fase5_panel_recordatorios_y_pdf():
 texto=(RAIZ/"AgendaPagina.tsx").read_text(encoding="utf-8")
 for token in ("PanelSeguimiento","/agenda/panel","/plantillas-recordatorio","/recordatorios","confirmar-rapido","/pdf","Exportar PDF diario"):
  assert token in texto
