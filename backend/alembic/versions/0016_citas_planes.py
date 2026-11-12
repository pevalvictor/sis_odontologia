"""integración de citas con planes"""
from alembic import op
import sqlalchemy as sa
revision="0016_citas_planes";down_revision="0015_agenda_diaria_fase1";branch_labels=None;depends_on=None
def upgrade():
 op.add_column("citas",sa.Column("plan_tratamiento_id",sa.Integer(),nullable=True))
 op.create_foreign_key("fk_citas_plan_tratamiento","citas","planes_tratamiento",["plan_tratamiento_id"],["id"],ondelete="SET NULL")
 op.create_index("ix_citas_plan_tratamiento_id","citas",["plan_tratamiento_id"])
def downgrade():
 op.drop_index("ix_citas_plan_tratamiento_id",table_name="citas");op.drop_constraint("fk_citas_plan_tratamiento","citas",type_="foreignkey");op.drop_column("citas","plan_tratamiento_id")
