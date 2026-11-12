"""dentición temporal y mixta"""
from alembic import op
import sqlalchemy as sa
revision="0008_denticion_pediatrica";down_revision="0007_permisos_fase_1";branch_labels=None;depends_on=None
def upgrade():
    op.add_column("odontogramas",sa.Column("tipo_denticion",sa.String(20),nullable=False,server_default="permanente"))
    op.add_column("piezas_odontograma",sa.Column("tipo_pieza",sa.String(20),nullable=False,server_default="permanente"))
    op.add_column("piezas_odontograma",sa.Column("estado_erupcion",sa.String(25),nullable=False,server_default="erupcionado"))
    op.add_column("piezas_odontograma",sa.Column("estado_pieza",sa.String(35),nullable=False,server_default="presente"))
    op.add_column("piezas_odontograma",sa.Column("perdida_prematura",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.add_column("piezas_odontograma",sa.Column("numero_pieza_sucesora",sa.Integer(),nullable=True))
    for nombre,tipo in [("condicion",sa.String(30)),("tipo_pieza",sa.String(20)),("estado_erupcion",sa.String(25)),("estado_pieza",sa.String(35)),("perdida_prematura",sa.Boolean()),("numero_pieza_sucesora",sa.Integer())]:op.add_column("hallazgos_dentales",sa.Column(nombre,tipo,nullable=True))
def downgrade():
    for nombre in ["numero_pieza_sucesora","perdida_prematura","estado_pieza","estado_erupcion","tipo_pieza","condicion"]:op.drop_column("hallazgos_dentales",nombre)
    for nombre in ["numero_pieza_sucesora","perdida_prematura","estado_pieza","estado_erupcion","tipo_pieza"]:op.drop_column("piezas_odontograma",nombre)
    op.drop_column("odontogramas","tipo_denticion")
