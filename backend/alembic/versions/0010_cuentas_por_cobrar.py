"""cuentas por cobrar y cuotas"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0010_cuentas_por_cobrar";down_revision="0009_sesiones_tratamiento";branch_labels=None;depends_on=None
nombres=["cuentas_por_cobrar","cuotas_cuenta_por_cobrar"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
 for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
