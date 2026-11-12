"""pagos mixtos, aplicaciones y devoluciones"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0012_pagos_y_devoluciones";down_revision="0011_caja_diaria";branch_labels=None;depends_on=None
nombres=["pagos","detalles_pago","aplicaciones_pago","devoluciones_pago","movimientos_caja"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
 for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
