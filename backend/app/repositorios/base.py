from typing import TypeVar, Generic, Type
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.base import Base
T = TypeVar("T", bound=Base)
class RepositorioBase(Generic[T]):
    def __init__(self, modelo: Type[T], sesion: Session): self.modelo, self.sesion = modelo, sesion
    def obtener(self, id_: int) -> T | None: return self.sesion.get(self.modelo, id_)
    def listar(self) -> list[T]: return list(self.sesion.scalars(select(self.modelo)))
    def crear(self, **datos) -> T:
        entidad = self.modelo(**datos); self.sesion.add(entidad); self.sesion.flush(); return entidad

