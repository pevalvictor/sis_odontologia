from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.rutas import router
from app.api.fase1 import router as router_fase1
from app.api.fase2 import router as router_fase2
from app.core.configuracion import configuracion
from app.db.sesion import SesionLocal

app = FastAPI(title=configuracion.nombre_app, version="0.1.0", description="API multi-clínica - Fase 0")
app.add_middleware(CORSMiddleware, allow_origins=configuracion.lista_origenes, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(router_fase1)
app.include_router(router_fase2)

@app.get("/salud")
def salud():
    with SesionLocal() as sesion: sesion.execute(text("SELECT 1"))
    return {"estado": "saludable"}

@app.exception_handler(Exception)
async def error_no_controlado(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detalle": "Error interno del servidor"})
