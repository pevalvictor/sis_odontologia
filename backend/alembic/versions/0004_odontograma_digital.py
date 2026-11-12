"""odontogramas, piezas y hallazgos"""
from alembic import op
from app.db.base import Base
from app import modelos  # noqa
revision="0004_odontograma_digital";down_revision="0003_historias_consultas";branch_labels=None;depends_on=None
nombres=["odontogramas","piezas_odontograma","hallazgos_dentales"]
def upgrade():Base.metadata.create_all(op.get_bind(),tables=[Base.metadata.tables[x] for x in nombres])
def downgrade():
    for x in reversed(nombres):Base.metadata.tables[x].drop(op.get_bind(),checkfirst=True)
