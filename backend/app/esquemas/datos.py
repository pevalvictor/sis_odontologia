from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class EsquemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class RegistroInicial(BaseModel):
    nombre_comercial: str = Field(min_length=2, max_length=150)
    razon_social: str | None = None
    ruc: str = Field(pattern=r"^\d{11}$")
    correo_clinica: EmailStr
    telefono: str | None = None
    direccion: str | None = None
    nombres_administrador: str = Field(min_length=2)
    apellidos_administrador: str = Field(min_length=2)
    correo_administrador: EmailStr
    nombre_usuario: str = Field(min_length=3)
    contrasena: str = Field(min_length=8)

class InicioSesion(BaseModel):
    identificador: str
    contrasena: str
    ruc: str | None = None

class RefrescarToken(BaseModel):
    refresh_token: str

class CerrarSesion(RefrescarToken): pass
class RecuperarContrasena(BaseModel):
    correo: EmailStr
    ruc: str = Field(pattern=r"^\d{11}$")

class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    tipo: str = "bearer"

class ClinicaActualizar(BaseModel):
    nombre_comercial: str | None = None
    razon_social: str | None = None
    correo: EmailStr | None = None
    telefono: str | None = None
    direccion: str | None = None
    logo_url: str | None = None
    zona_horaria: str | None = None
    moneda: str | None = Field(default=None, min_length=3, max_length=3)
    igv_porcentaje: Decimal | None = Field(default=None, ge=0, le=100)

class SedeCrear(BaseModel):
    nombre: str
    direccion: str
    telefono: str | None = None
    correo: EmailStr | None = None
    cantidad_consultorios: int = Field(default=1, ge=1)
    estado: bool = True

class SedeActualizar(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    cantidad_consultorios: int | None = Field(default=None, ge=1)
    estado: bool | None = None

class UsuarioCrear(BaseModel):
    nombres: str
    apellidos: str
    documento_identidad: str | None = None
    correo: EmailStr
    telefono: str | None = None
    nombre_usuario: str
    contrasena: str = Field(min_length=8)
    roles_ids: list[int] = []

class UsuarioActualizar(BaseModel):
    nombres: str | None = None
    apellidos: str | None = None
    documento_identidad: str | None = None
    correo: EmailStr | None = None
    telefono: str | None = None
    nombre_usuario: str | None = None
    contrasena: str | None = Field(default=None, min_length=8)
    roles_ids: list[int] | None = None

class EstadoActualizar(BaseModel): estado: bool

class RolCrear(BaseModel):
    nombre: str
    descripcion: str | None = None
    estado: bool = True

class RolActualizar(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    estado: bool | None = None

class PermisoRol(BaseModel):
    permiso_id: int
    puede_ver: bool = False
    puede_crear: bool = False
    puede_editar: bool = False
    puede_eliminar: bool = False
    puede_exportar: bool = False

class PermisosRolActualizar(BaseModel): permisos: list[PermisoRol]
class ModuloActualizar(BaseModel): activo: bool
