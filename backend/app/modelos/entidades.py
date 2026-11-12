from datetime import datetime
from decimal import Decimal
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class FechasMixin:
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Clinica(FechasMixin, Base):
    __tablename__ = "clinicas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_comercial: Mapped[str] = mapped_column(String(150))
    razon_social: Mapped[str | None] = mapped_column(String(180))
    ruc: Mapped[str] = mapped_column(String(11), unique=True)
    correo: Mapped[str] = mapped_column(String(180))
    telefono: Mapped[str | None] = mapped_column(String(30))
    direccion: Mapped[str | None] = mapped_column(String(250))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    zona_horaria: Mapped[str] = mapped_column(String(60), default="America/Lima")
    moneda: Mapped[str] = mapped_column(String(3), default="PEN")
    igv_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=18)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

class Sede(FechasMixin, Base):
    __tablename__ = "sedes"
    __table_args__ = (UniqueConstraint("clinica_id", "nombre"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    direccion: Mapped[str] = mapped_column(String(250))
    telefono: Mapped[str | None] = mapped_column(String(30))
    correo: Mapped[str | None] = mapped_column(String(180))
    cantidad_consultorios: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

class Usuario(FechasMixin, Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("clinica_id", "correo"), UniqueConstraint("clinica_id", "nombre_usuario"))
    id: Mapped[int] = mapped_column(primary_key=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id", ondelete="CASCADE"), index=True)
    nombres: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    documento_identidad: Mapped[str | None] = mapped_column(String(20))
    correo: Mapped[str] = mapped_column(String(180))
    telefono: Mapped[str | None] = mapped_column(String(30))
    nombre_usuario: Mapped[str] = mapped_column(String(80))
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    estado: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Modulo(Base):
    __tablename__ = "modulos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    codigo: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

class Rol(FechasMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("clinica_id", "nombre"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    descripcion: Mapped[str | None] = mapped_column(Text)
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

class Permiso(Base):
    __tablename__ = "permisos"
    id: Mapped[int] = mapped_column(primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(100))
    codigo: Mapped[str] = mapped_column(String(120), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UsuarioRol(Base):
    __tablename__ = "usuarios_roles"
    __table_args__ = (UniqueConstraint("usuario_id", "rol_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class RolPermiso(Base):
    __tablename__ = "roles_permisos"
    __table_args__ = (UniqueConstraint("rol_id", "permiso_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    permiso_id: Mapped[int] = mapped_column(ForeignKey("permisos.id", ondelete="CASCADE"))
    puede_ver: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_crear: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_editar: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_eliminar: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_exportar: Mapped[bool] = mapped_column(Boolean, default=False)

class ClinicaModulo(Base):
    __tablename__ = "clinicas_modulos"
    __table_args__ = (UniqueConstraint("clinica_id", "modulo_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id", ondelete="CASCADE"), index=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"))
    activo: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_activacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class SesionUsuario(Base):
    __tablename__ = "sesiones_usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    identificador_token: Mapped[str] = mapped_column(String(36), unique=True)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocada: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BitacoraAuditoria(Base):
    __tablename__ = "bitacora_auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    clinica_id: Mapped[int] = mapped_column(ForeignKey("clinicas.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    accion: Mapped[str] = mapped_column(String(80))
    modulo: Mapped[str] = mapped_column(String(100))
    entidad: Mapped[str] = mapped_column(String(100))
    entidad_id: Mapped[str | None] = mapped_column(String(50))
    datos_anteriores: Mapped[dict | None] = mapped_column(JSON)
    datos_nuevos: Mapped[dict | None] = mapped_column(JSON)
    direccion_ip: Mapped[str | None] = mapped_column(String(50))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
