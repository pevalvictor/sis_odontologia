"""sesiones de tratamiento"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0009_sesiones_tratamiento";down_revision="0008_denticion_pediatrica";branch_labels=None;depends_on=None
nombres=["sesiones_tratamiento","insumos_sesion"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
 for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
