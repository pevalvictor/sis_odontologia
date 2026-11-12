import os
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from app.main import app
from app.db.base import Base
from app.db.sesion import obtener_sesion

motor=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
SesionPrueba=sessionmaker(bind=motor,expire_on_commit=False)
@pytest.fixture(autouse=True)
def base():
    Base.metadata.create_all(motor);yield;Base.metadata.drop_all(motor)
@pytest.fixture
def cliente():
    def sesion():
        with SesionPrueba() as s: yield s
    app.dependency_overrides[obtener_sesion]=sesion
    with TestClient(app,raise_server_exceptions=True) as c: yield c
    app.dependency_overrides.clear()

