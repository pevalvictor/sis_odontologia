"""caja diaria y movimientos"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0011_caja_diaria";down_revision="0010_cuentas_por_cobrar";branch_labels=None;depends_on=None
nombres=["cajas"]
def upgrade():
 Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres]);op.create_index("uq_caja_abierta_sede_fecha","cajas",["clinica_id","sede_id","fecha_operativa"],unique=True,postgresql_where=__import__('sqlalchemy').text("estado = 'abierta'"))
def downgrade():
 op.drop_index("uq_caja_abierta_sede_fecha",table_name="cajas")
 for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
