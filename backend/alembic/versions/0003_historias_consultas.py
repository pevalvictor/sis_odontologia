"""historias, consultas y evoluciones"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0003_historias_consultas";down_revision="0002_nucleo_pacientes";branch_labels=None;depends_on=None
nombres=["historias_clinicas","consultas_clinicas","evoluciones_clinicas"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
    for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
