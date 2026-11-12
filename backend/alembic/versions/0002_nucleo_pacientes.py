"""pacientes, antecedentes y alergias"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0002_nucleo_pacientes";down_revision="0001_base_fase_0";branch_labels=None;depends_on=None
nombres=["pacientes","antecedentes_medicos","alergias_paciente"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
    for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
