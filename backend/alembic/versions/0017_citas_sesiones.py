"""integración de citas con sesiones"""
from alembic import op
revision="0017_citas_sesiones";down_revision="0016_citas_planes";branch_labels=None;depends_on=None
def upgrade():
 op.drop_constraint("ck_citas_estado_fase1","citas",type_="check")
 op.create_check_constraint("ck_citas_estado_fase1","citas","estado IN ('programada','confirmada','en_atencion','atendida','cancelada','no_asistio')")
 op.create_index("ix_sesiones_tratamiento_cita_id","sesiones_tratamiento",["cita_id"])
def downgrade():
 op.drop_index("ix_sesiones_tratamiento_cita_id",table_name="sesiones_tratamiento");op.execute("UPDATE citas SET estado='confirmada' WHERE estado='en_atencion'");op.drop_constraint("ck_citas_estado_fase1","citas",type_="check");op.create_check_constraint("ck_citas_estado_fase1","citas","estado IN ('programada','confirmada','atendida','cancelada','no_asistio')")
