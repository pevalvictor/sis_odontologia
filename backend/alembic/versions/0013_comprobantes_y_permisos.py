"""comprobantes internos y permisos fase 2"""
from alembic import op
from sqlalchemy.orm import Session
from app.db.base import Base
from app import modelos  # noqa
from app.db.semillas import sembrar_fase2
revision="0013_comprobantes_y_permisos";down_revision="0012_pagos_y_devoluciones";branch_labels=None;depends_on=None
def upgrade():
 Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables["comprobantes_internos"]])
 with Session(bind=op.get_bind()) as s:sembrar_fase2(s);s.commit()
def downgrade():Base.metadata.tables["comprobantes_internos"].drop(op.get_bind(),checkfirst=True)
