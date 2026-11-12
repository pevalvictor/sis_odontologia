"""agenda diaria fase 1"""
from alembic import op
import sqlalchemy as sa
revision="0015_agenda_diaria_fase1";down_revision="0014_alcance_procedimientos_plan";branch_labels=None;depends_on=None
def upgrade():
 op.add_column("citas",sa.Column("tipo_cita",sa.String(30),nullable=True,server_default="otro"))
 op.execute("UPDATE citas SET tipo_cita='otro' WHERE tipo_cita IS NULL")
 op.execute("UPDATE citas SET estado='no_asistio' WHERE estado='inasistencia'")
 op.execute("UPDATE citas SET estado='programada' WHERE estado NOT IN ('programada','confirmada','atendida','cancelada','no_asistio')")
 op.alter_column("citas","tipo_cita",nullable=False,server_default=None)
 op.create_check_constraint("ck_citas_estado_fase1","citas","estado IN ('programada','confirmada','atendida','cancelada','no_asistio')")
 op.create_check_constraint("ck_citas_tipo_fase1","citas","tipo_cita IN ('evaluacion_inicial','control','procedimiento','urgencia','revision','ortodoncia','profilaxis','blanqueamiento','otro')")
def downgrade():
 op.drop_constraint("ck_citas_tipo_fase1","citas",type_="check");op.drop_constraint("ck_citas_estado_fase1","citas",type_="check");op.drop_column("citas","tipo_cita")
