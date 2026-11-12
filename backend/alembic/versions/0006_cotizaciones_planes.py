"""cotizaciones y planes de tratamiento"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0006_cotizaciones_planes";down_revision="0005_agenda_citas";branch_labels=None;depends_on=None
nombres=["cotizaciones","detalles_cotizacion","planes_tratamiento","detalles_plan_tratamiento"]
def upgrade():
    Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
    op.create_foreign_key("fk_hallazgos_detalle_plan","hallazgos_dentales","detalles_plan_tratamiento",["detalle_plan_tratamiento_id"],["id"],ondelete="SET NULL")
def downgrade():
    op.drop_constraint("fk_hallazgos_detalle_plan","hallazgos_dentales",type_="foreignkey")
    for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
