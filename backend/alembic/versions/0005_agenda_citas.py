"""consultorios, tipos de cita y citas"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0005_agenda_citas";down_revision="0004_odontograma_digital";branch_labels=None;depends_on=None
nombres=["consultorios","tipos_cita","citas"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
    for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
